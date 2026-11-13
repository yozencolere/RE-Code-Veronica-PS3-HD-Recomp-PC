/* Opt-in pacing experiment. Keep the guest's real-time delta calculation.
 * The first vblank-only experiment did not unlock this title's 30 FPS cap.
 * Addresses matched independently in each region's lifted frame routine.
 */
#include "ppu_recomp.h"
#include "cv_version.h"
#include "cv_scene_region.h"
#include "cv_fps_clock.h"
#include "cv_item_interpolation.h"
#include "cv_inventory_ui_interpolation.h"
#include "cv_fps_input.h"
#include "cv_options.h"
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <ctime>
#include <chrono>
#include <atomic>
void CV_OG_FRAME_PACE(ppu_context*);
// These methods are invoked virtually through the guest function registry.
// There are no direct call sites in any of the three lifted images.
#if defined(CV_REGION_JP)
#define CV_BIO_UPDATE func_0020E9C0
static constexpr uint32_t bio_update_address=0x0020E9C0;
#elif defined(CV_REGION_US)
#define CV_BIO_UPDATE func_0020E0D0
static constexpr uint32_t bio_update_address=0x0020E0D0;
#else
#define CV_BIO_UPDATE func_00210070
static constexpr uint32_t bio_update_address=0x00210070;
#endif
void CV_BIO_UPDATE(ppu_context*);
extern "C" void ppu_register_function(uint64_t,void (*)(ppu_context*));
extern "C" void rsx_d3d12_pose_scene(uint32_t);
extern "C" void rsx_d3d12_camera_cut(void);
extern "C" void rsx_d3d12_camera_hold(int);
extern "C" int rsx_d3d12_pose_replay_enabled(void);
extern "C" PPU_THREAD_LOCAL void (*g_trampoline_fn)(void*);
static void drain_scene(ppu_context* ctx) {
    while(g_trampoline_fn) {auto fn=g_trampoline_fn;g_trampoline_fn=nullptr;fn(ctx);}
}
namespace {
// Publish pacing to a possible engine worker as one consistent snapshot.
std::atomic<uint64_t> timing{0};
float read_float(uint32_t a) { uint32_t b=vm_read32(a); float f; std::memcpy(&f,&b,4); return f; }
void write_float(uint32_t a,float f) { uint32_t b; std::memcpy(&b,&f,4);vm_write32(a,b); }
bool profile_enabled() {
    static const bool on=[] {const char* e=std::getenv("CV_FRAME_PROFILE");return e&&std::strcmp(e,"1")==0;}();
    return on;
}
bool enabled() {
    static const bool on=[] {const char* e=std::getenv("CV_FPS_TEST_60");return e&&std::strcmp(e,"1")==0;}();
    return on;
}
// CV_FPS_UNLOCKED=1 (benchmark shortcut only): the engine cap goes to 1000
// instead of 60, so the frame rate shows how far the machine can go.
float frame_cap() {
    static const float cap=[] {const char* e=std::getenv("CV_FPS_UNLOCKED");return e&&std::strcmp(e,"1")==0?1000.0f:60.0f;}();
    return cap;
}
// The renderer presents every native 30 Hz frame twice (interpolated, then
// recorded): the guest keeps its own pacing, one update and one draw a tick.
bool replay() {
    static const bool on=rsx_d3d12_pose_replay_enabled()!=0;
    return on;
}
}
extern "C" bool cv_fps_elapsed_ticks(float* out) {
    const uint64_t sample=timing.load(std::memory_order_acquire);
    if(!(sample>>32))return false;
    const uint32_t bits=static_cast<uint32_t>(sample);
    std::memcpy(out,&bits,sizeof bits);
    return true;
}
void CV_FN_FRAME_PACE(ppu_context* ctx) {
    if(!enabled()) { CV_OG_FRAME_PACE(ctx);return; }
    const uint32_t object=static_cast<uint32_t>(ctx->gpr[3]);
    const uint32_t previous=vm_read32(object+0x64);
    const uint8_t mode=vm_read8(object+0x68);
    const float base=read_float(object+0x60),cap=read_float(object+0x64);
    // Game init writes 30 into +60. Fixed-step mode (+68 != 0) waits
    // for one full logical tick. Select the original variable-step path,
    // with a 60 FPS cap: target delta is 30/60 = 0.5 logical ticks.
    // Keep the base at 30 so elapsed game time is not doubled.
    const bool change=base==30.0f && cap>=30.0f && cap<=3000.0f && mode<=1 && !replay();
    if(change) {write_float(object+0x64,frame_cap());vm_write8(object+0x68,0);}
    static bool announced=false;
    if(!announced) {
        std::fprintf(stderr,"[FPS60 %s] engine object=%08X base=%g cap=%g mode=%u override=%u\n",CV_TITLE_ID,object,base,cap,unsigned(mode),unsigned(change));
        announced=true;
    }
    CV_OG_FRAME_PACE(ctx);
    timing.store(change?(0x100000000ull|vm_read32(object+0x90)):0,std::memory_order_release);
    // No lasting guest setting. Leave a change made by the original routine alone.
    if(change) {
        if(read_float(object+0x64)==frame_cap())vm_write32(object+0x64,previous);
        if(vm_read8(object+0x68)==0)vm_write8(object+0x68,mode);
    }
    if(!profile_enabled())return;
    using Clock=std::chrono::steady_clock;
    static auto start=Clock::now();static unsigned frames=0;static double steps=0;
    frames++;steps+=read_float(object+0x90);
    const auto now=Clock::now();const double elapsed=std::chrono::duration<double>(now-start).count();
    if(elapsed>=5.0) {
        std::fprintf(stderr,"[FPS60 %s] pacing_calls_per_second=%.2f delta_ticks_per_second=%.2f last_step=%.4f override=%u\n",CV_TITLE_ID,frames/elapsed,steps/elapsed,read_float(object+0x90),unsigned(change));
        start=now;frames=0;steps=0;
    }
}

namespace {
#include "cv_smooth_animation.h"
// fork, diagnostic (CV_DOOR_LOG=1, US only): after each game tick, the words
// of the door scene object (0x00CA72F0, used by func_0003B810), the object it
// points to at +0x28, the camera and the scene system that changed since the
// previous tick, while a door is active. Written to door-log.txt.
void door_log(unsigned tick_in_frame) {
#if defined(CV_REGION_US)
    static const bool on=[] {const char* e=std::getenv("CV_DOOR_LOG");return e&&std::strcmp(e,"1")==0;}();
    if(!on)return;
    static std::FILE* file=std::fopen("door-log.txt","w");
    if(!file)return;
    struct Region {const char* name;uint32_t base,size;};
    const uint32_t door=0x00CA72F0u,linked=vm_read32(door+0x28),system=vm_read32(CV_SCENE_SYSTEM);
    const Region regions[]={{"door",door,0x200},{"door28",linked,0x200},{"cam",CV_SCENE_CAMERA,0x100},{"sys",system+0x60,0x20}};
    static uint32_t last[4][0x80];static uint32_t last_base[4];static unsigned quiet=0;static unsigned long serial=0;
    const bool active=vm_read32(door+0x8)!=0||(system&&(vm_read32(system+0x68)&0x80));
    serial++;
    if(!active) {if(quiet<2) {quiet++;std::fprintf(file,"-- tick %lu inactive\n",serial);std::fflush(file);}return;}
    quiet=0;
    std::fprintf(file,"== tick %lu (%u in frame) t=%ld\n",serial,tick_in_frame,(long)std::clock());
    for(unsigned r=0;r<4;r++) {
        const Region& g=regions[r];
        if(!g.base)continue;
        const bool fresh=g.base!=last_base[r];last_base[r]=g.base;
        for(uint32_t o=0;o<g.size;o+=4) {
            const uint32_t v=vm_read32(g.base+o);
            if(fresh||v!=last[r][o/4]) {
                float f;std::memcpy(&f,&v,4);
                std::fprintf(file,"  %s+%03X %08X (%g)%s\n",g.name,o,v,(double)f,fresh?" *":"");
            }
            last[r][o/4]=v;
        }
    }
    std::fflush(file);
#else
    (void)tick_in_frame;
#endif
}
// fork: 60 FPS door transitions (US). During a door, BioUpdate drives
// func_0003B810, which updates the door scene object at 0x00CA72F0 and draws it
// (camera from +0x58/+0x5C/+0x60 and angles +0x70/+0x74/+0x78, fade +0x3C).
// Bit 0x80 of +0x08 makes it skip every update step (its own pause path): no
// callbacks, no counter, no sound request, only the drawing. On a rendered
// frame with no game tick, one more game update runs with the door paused and
// the camera, fade and door model parts carried half a tick further along their
// last step; then those values and the in-game clock are put back.
// Drawing the door outside a game update stalls its model renderer, hence the
// whole update. CV_DOOR_SMOOTH=0 keeps the original repeated frame;
// CV_DOOR_LOG=1 writes door-log.txt / door60-log.txt.
#if defined(CV_REGION_US)
namespace door60 {
constexpr uint32_t kDoor=0x00CA72F0u,kSize=0x200;
struct State {bool valid=false;uint32_t counter=0;float pos[3]{},fade=0;uint32_t angle[3]{};};
State prev,cur;bool live=false;
// The door model (+0xC4): a tree of parts drawn by func_001D08F4. Each part has
// flags at +0, a translation at +0x08 (3 floats), a rotation at +0x14 (3 ints,
// 0x10000 = one turn) and a scale at +0x20 (3 floats); first child +0x2C, next
// sibling +0x30. The update callbacks animate them; the paused extra update
// does not, so they are carried half a step here as well.
struct Part {uint32_t addr=0;float pos[3]{},scale[3]{};uint32_t rot[3]{};};
constexpr unsigned kParts=128;
Part parts_prev[kParts],parts_cur[kParts],parts_scratch[kParts];unsigned parts_prev_n=0,parts_cur_n=0;
unsigned read_parts(Part* out) {
    uint32_t stack[kParts];unsigned top=0,n=0;
    if(const uint32_t root=vm_read32(kDoor+0xC4))stack[top++]=root;
    while(top&&n<kParts) {
        const uint32_t node=stack[--top];
        if(!node||node>=0xF0000000u)continue;
        Part& p=out[n++];p.addr=node;
        for(unsigned i=0;i<3;i++) {
            p.pos[i]=read_float(node+0x08+4*i);p.rot[i]=vm_read32(node+0x14+4*i);p.scale[i]=read_float(node+0x20+4*i);
        }
        const uint32_t child=vm_read32(node+0x2C),next=vm_read32(node+0x30);
        if(next&&top<kParts)stack[top++]=next;
        if(child&&top<kParts)stack[top++]=child;
    }
    return n;
}
void write_part(const Part& p) {
    for(unsigned i=0;i<3;i++) {
        write_float(p.addr+0x08+4*i,p.pos[i]);vm_write32(p.addr+0x14+4*i,p.rot[i]);write_float(p.addr+0x20+4*i,p.scale[i]);
    }
}
bool enabled() {
    static const bool on=[] {const char* e=std::getenv("CV_DOOR_SMOOTH");return !(e&&e[0]=='0');}();
    return on;
}
State read() {
    State s;s.valid=true;s.counter=vm_read32(kDoor+0x10);
    for(unsigned i=0;i<3;i++) {s.pos[i]=read_float(kDoor+0x58+4*i);s.angle[i]=vm_read32(kDoor+0x70+4*i);}
    s.fade=read_float(kDoor+0x3C);
    return s;
}
// After each game tick: the door drew this tick when its counter advanced by one.
void after_tick() {
    const uint32_t flags=vm_read32(kDoor+0x8);
    const State now=read();
    // Two consecutive door images, well inside the door (never its first ones,
    // where the previous state is the room's and the scene is still being set up).
    const bool stepped=cur.valid&&cur.counter>=3&&now.counter==cur.counter+1&&!(flags&0xC0);
    prev=stepped?cur:State{};
    cur=now;live=stepped;
    std::memcpy(parts_prev,parts_cur,sizeof parts_cur);parts_prev_n=parts_cur_n;
    parts_cur_n=read_parts(parts_cur);
}
void no_tick() {live=false;prev=State{};cur=State{};parts_prev_n=parts_cur_n=0;}
void draw_between(const ppu_context& incoming,double phase) {
    if(!enabled()||!live||!prev.valid||!cur.valid)return;
    // The extra image is shown halfway between two presented game images,
    // whatever the logic clock's phase says (it drifts between 0.5 and 0.9).
    (void)phase;
    const float t=0.5f;
    uint8_t saved[kSize];
    for(uint32_t o=0;o<kSize;o+=4){const uint32_t v=vm_read32(kDoor+o);std::memcpy(saved+o,&v,4);}
    for(unsigned i=0;i<3;i++) {
        write_float(kDoor+0x58+4*i,cur.pos[i]+(cur.pos[i]-prev.pos[i])*t);
        const int delta=int((cur.angle[i]-prev.angle[i]+0x8000u)&0xFFFFu)-0x8000;
        vm_write32(kDoor+0x70+4*i,cur.angle[i]+static_cast<int>(std::lround(delta*t)));
    }
    float fade=cur.fade+(cur.fade-prev.fade)*t;
    if(fade<0)fade=0;if(fade>1)fade=1;
    write_float(kDoor+0x3C,fade);
    // Door parts: same tree as last tick (part by part, by address).
    unsigned moved=0;
    const bool same_tree=parts_prev_n==parts_cur_n&&read_parts(parts_scratch)==parts_cur_n;
    if(same_tree)for(unsigned k=0;k<parts_cur_n;k++) {
        const Part& a=parts_prev[k];const Part& b=parts_cur[k];
        if(a.addr!=b.addr||parts_scratch[k].addr!=b.addr)continue;
        Part m=b;
        for(unsigned i=0;i<3;i++) {
            m.pos[i]=b.pos[i]+(b.pos[i]-a.pos[i])*t;m.scale[i]=b.scale[i]+(b.scale[i]-a.scale[i])*t;
            const int delta=int((b.rot[i]-a.rot[i]+0x8000u)&0xFFFFu)-0x8000;
            m.rot[i]=b.rot[i]+static_cast<int>(std::lround(delta*t));
        }
        if(std::memcmp(&m,&b,sizeof m)!=0)moved++;
        write_part(m);
    }
    // CV_DOOR_LOG=1: one line before and one after each extra door image.
    static const bool log=[] {const char* e=std::getenv("CV_DOOR_LOG");return e&&std::strcmp(e,"1")==0;}();
    static std::FILE* f=log?std::fopen("door60-log.txt","w"):nullptr;
    if(f){std::fprintf(f,"counter=%u phase=%.3f z %.4f->%.4f drawn %.4f fade %.3f ...",cur.counter,phase,
        (double)prev.pos[2],(double)cur.pos[2],(double)read_float(kDoor+0x60),(double)fade);std::fflush(f);}
    // Drawing the door outside a game update stalls its model renderer
    // (func_001D08F4/001D0208). So the extra image is a whole game update with
    // the door paused (bit 0x80: func_0003B810 only draws, its state machine
    // keeps waiting on it), the in-game clock kept as it was.
    const uint32_t flags_before=vm_read32(kDoor+0x8);
    vm_write32(kDoor+0x8,flags_before|0x80);
    const uint32_t clock_before=vm_read32(CV_SRT_TIME);
    ppu_context call=incoming;
    CV_BIO_UPDATE(&call);
    vm_write32(CV_SRT_TIME,clock_before);
    // Put back only what was changed here; whatever the update itself did stays.
    const uint32_t flags_now=vm_read32(kDoor+0x8);
    if(!(flags_before&0x80))vm_write32(kDoor+0x8,flags_now&~0x80u);
    const auto put_back=[&](uint32_t o) {uint32_t v;std::memcpy(&v,saved+o,4);vm_write32(kDoor+o,v);};
    for(uint32_t o:{0x3Cu,0x58u,0x5Cu,0x60u,0x70u,0x74u,0x78u})put_back(o);
    if(same_tree)for(unsigned k=0;k<parts_cur_n;k++)if(parts_scratch[k].addr==parts_cur[k].addr)write_part(parts_cur[k]);
    if(f){std::fprintf(f," ok (counter now %u, parts %u, moving %u)\n",vm_read32(kDoor+0x10),parts_cur_n,moved);std::fflush(f);}
}
}
#endif
void bio_update_30hz(ppu_context* ctx) {
    const bool smooth=cv_options::enabled("CV_SMOOTH_ANIMATION");
    const bool input_fix=cv_options::enabled("CV_INPUT_COMFORT");
    if(smooth)cv_item_interpolation::restore();
    cv_inventory_ui::restore();
    native_scene_restore();
    static thread_local cv_fps::LogicClock clock;
    static thread_local cv_fps_input::Latch input;
    const uint64_t sample=timing.load(std::memory_order_acquire);
    unsigned count=1;float elapsed_ticks=1;
    if(!(sample>>32)) {
        // Native pacing (replay or unrecognised object): one update a frame.
        clock.reset();input.reset();cv_item_interpolation::reset();cv_inventory_ui::reset();CV_BIO_UPDATE(ctx);
#if defined(CV_REGION_US)
        door60::no_tick();
#endif
        if(!replay())return;
    }else {
        uint32_t bits=static_cast<uint32_t>(sample);std::memcpy(&elapsed_ticks,&bits,4);
        count=clock.advance(elapsed_ticks);
        if(input_fix)input.capture();
        // The virtual method is void. Skipped updates leave the incoming guest
        // context alone; each executed update gets the same incoming arguments.
        const ppu_context incoming=*ctx;
        for(unsigned i=0;i<count;i++) {
            *ctx=incoming;
            if(input_fix)input.begin_tick(i==0);
            cv_inventory_ui::begin();
            native_scene_before();
            CV_BIO_UPDATE(ctx);
            door_log(i);
#if defined(CV_REGION_US)
            door60::after_tick();
#endif
            if(input_fix)input.end_tick();
            native_scene_after();
            if(smooth)cv_item_interpolation::capture();
            cv_inventory_ui::capture();
        }
        render_scene_between_ticks(ctx,count,clock.phase());
#if defined(CV_REGION_US)
        if(count==0)door60::draw_between(incoming,clock.phase());
#endif
        if(smooth)cv_item_interpolation::render(clock.phase());
        cv_inventory_ui::render(clock.phase());
    }
    // Self-destruct countdown (system+0x1B170 on, +0x1B174 frames left at 60
    // a second): the game takes 2 off once per DRAWN frame, outside the 30 Hz
    // logic, so at 60 FPS it ran twice as fast. Allow only 2 per logic update
    // and give back the rest.
    {
        static uint32_t last=0;static unsigned budget=0;
        const uint32_t system=vm_read32(CV_SCENE_SYSTEM);
        const uint32_t on=system?vm_read32(system+0x1B170):0,left=system?vm_read32(system+0x1B174):0;
        if(!on||!left||!last||left>last){last=on?left:0;budget=0;}
        else {
            budget=std::min(budget+2*count,8u);
            const uint32_t taken=last-left;
            if(taken>budget){vm_write32(system+0x1B174,left+(taken-budget));last=left+(taken-budget);budget=0;}
            else {budget-=taken;last=left;}
        }
    }
    static const bool interpolate=[] {const char* e=std::getenv("CV_RENDER_INTERPOLATION");return e&&std::strcmp(e,"1")==0;}();
    if(interpolate) {
        static const uint32_t markers[]={0x3D650,0x3C4FC,0x3A4D0,0x3E814};
        uint32_t c=vm_read8(CV_SRT_CHARACTER),scene=0;
        if(c<4&&vm_read32(CV_SRT_RDX)==markers[c])scene=0x80000000u|(uint32_t(vm_read8(CV_SRT_ROOM))<<16)|(uint32_t(vm_read8(CV_SRT_ROOM+1))<<8)|c;
        rsx_d3d12_pose_scene(scene);
    }
    if(!profile_enabled())return;
    using Clock=std::chrono::steady_clock;
    static thread_local auto start=Clock::now();
    static thread_local unsigned draws=0,updates=0;
    draws++;updates+=count;
    const auto now=Clock::now();double seconds=std::chrono::duration<double>(now-start).count();
    if(seconds>=5.0) {
        std::fprintf(stderr,"[FPS60-LOGIC %s] render_updates_per_second=%.2f game_updates_per_second=%.2f ticks=%.4f\n",CV_TITLE_ID,draws/seconds,updates/seconds,elapsed_ticks);
        draws=0;updates=0;start=now;
    }
}
}
// True while native 60 FPS rebuilds the frame: the extra scene pass then
// drops the game's own 2D layer (the self-destruct countdown), so the port
// draws that countdown itself (cv_combat_hud.cpp). Read from the render thread.
extern "C" int cv_native_scene_replacing(void) {
    return enabled()&&cv_options::enabled("CV_SMOOTH_ANIMATION")&&native_scene_ready()?1:0;
}
extern "C" void cv_fps_register_game_update() {
    const char* raw=std::getenv("CV_FPS_BENCHMARK_RAW");
    if(!enabled())return;
    if(raw&&std::strcmp(raw,"1")==0) {
        std::fprintf(stderr,"[FPS60] RAW benchmark: game logic still runs once per rendered frame\n");return;
    }
    ppu_register_function(bio_update_address,bio_update_30hz);
    if(cv_options::enabled("CV_SMOOTH_ANIMATION")) {
        ppu_register_function(uint32_t(CV_SCENE_PREPARE_CUT),native_prepare_cut);
        ppu_register_function(uint32_t(CV_SCENE_HD_UPDATE),inspection_hd_update);
    }
    std::fprintf(stderr,"[FPS60] 30 Hz game update experiment registered at %08X; rendering kept separate\n",bio_update_address);
}
