#pragma once
// fork: European text in the US release (CV_NATIVE_LANGUAGE_ROOT).
// The European executable keeps two glyph-advance tables and picks one with a
// flag set from the system language: English uses the table the US release
// also has; French, German, Italian and Spanish use a second one (EU EBOOT
// 0x87A386) matching the European font atlas. The US executable only has the
// English table, so the European atlas came out with English advances (and
// accented slots past entry 127 read a string's bytes as widths).
// This copies the European table over the US one, once, after loading the
// exact US ELF. Code, files and the European installation are not changed.
// CV_EU_TEXT_METRICS=0 turns it off (for comparisons).
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include "cv_eu_text_metrics_data.h"
// The glyph limit of the US text routines (lifted `cmpwi rX,108`, made a
// variable by tools/cv_fork_glyph_limit.py): glyphs at or past it take the
// kanji path. The European code uses 162 for its non-English languages, whose
// accented letters are slots 108..161 of the European atlas.
extern "C" int cv_glyph_limit;
inline void cv_eu_text_metrics_install() {
    if(std::strcmp(CV_TITLE_ID,"NPUB30467"))return;
    const char* root=std::getenv("CV_NATIVE_LANGUAGE_ROOT");if(!root||!*root)return;
    const char* ptbr=std::getenv("CV_PTBR_ASSET_ROOT");if(ptbr&&*ptbr)return;
    const char* system=std::getenv("PS3_SYSTEM_LANGUAGE");
    if(!system||!std::strcmp(system,"1")){std::fprintf(stderr,"[EU-METRICS] English: US advances kept\n");return;}
    const char* off=std::getenv("CV_EU_TEXT_METRICS");
    if(off&&!std::strcmp(off,"0")){std::fprintf(stderr,"[EU-METRICS] disabled (CV_EU_TEXT_METRICS=0)\n");return;}
    const unsigned table=0x8780BCu;
    if(!vm_base||(ppu_vm_size!=0&&ppu_vm_size<table+sizeof kCvEuWidthsB)){
        std::fprintf(stderr,"[EU-METRICS] invalid guest mapping; not applied\n");return;
    }
    // Fail closed on another binary or an already modified table.
    if(std::memcmp(vm_base+table,kCvUsWidthsExpected,sizeof kCvUsWidthsExpected)){
        std::fprintf(stderr,"[EU-METRICS] unexpected US metrics; not applied\n");return;
    }
    // Language-dependent constants of the European text code that the US code
    // reads only in their English form, at sites where every US read matches a
    // European language branch (aligned against EU EBOOT, flag 0xAD33FC):
    // word-space advances 14 -> 16 (EU 0x160D64, 0x160F88, 0x1623B0), a text
    // advance 20 -> 16 (EU 0x162F1C) and a box origin x 68 -> 64 (EU 0x87A2D8).
    struct FloatPatch{unsigned address;float english,european;};
    static const FloatPatch floats[]={
        {0x15FEACu,14.f,16.f},{0x16004Cu,14.f,16.f},{0x161204u,14.f,16.f},
        {0x161BC8u,20.f,16.f},{0x87808Cu,68.f,64.f}};
    auto read_float=[](unsigned a){const uint8_t* p=vm_base+a;uint32_t w=(uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|p[3];float f;std::memcpy(&f,&w,4);return f;};
    const char* layout=std::getenv("CV_EU_LAYOUT");   // CV_EU_LAYOUT=0: widths only (comparisons)
    bool floats_ok=!(layout&&!std::strcmp(layout,"0"));
    for(const auto& f:floats)if(read_float(f.address)!=f.english){floats_ok=false;std::fprintf(stderr,"[EU-METRICS] unexpected constant at 0x%X; layout constants not applied\n",f.address);break;}
    if(floats_ok)for(const auto& f:floats){uint32_t w;std::memcpy(&w,&f.european,4);uint8_t* p=vm_base+f.address;p[0]=uint8_t(w>>24);p[1]=uint8_t(w>>16);p[2]=uint8_t(w>>8);p[3]=uint8_t(w);}
    std::memcpy(vm_base+table,kCvEuWidthsB,sizeof kCvEuWidthsB);
    cv_glyph_limit=162;
    if(floats_ok)std::fprintf(stderr,"[EU-METRICS] %zu European layout constants installed\n",sizeof floats/sizeof floats[0]);
    std::fprintf(stderr,"[EU-METRICS] European advances installed (%zu glyph slots, glyph limit %d, language %s)\n",sizeof kCvEuWidthsB,cv_glyph_limit,system);
}
