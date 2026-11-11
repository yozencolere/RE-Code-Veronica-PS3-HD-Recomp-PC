"""Applique la correction « retrait d'un demi-texel par quad » a rsx_d3d12_backend.c (une seule fois)."""
import shutil, sys
p = r'E:\Recomp\Code_Veronica_PC\libs\video\rsx_d3d12_backend.c'
shutil.copy2(p, r'E:\Recomp\_sauvegardes_orig\rsx_d3d12_backend.avant_inset.c')
s = open(p, 'rb').read().decode('latin-1')
nl = '\r\n' if '\r\n' in s else '\n'
def rep(old, new, count=1):
    global s
    old = old.replace('\n', nl); new = new.replace('\n', nl)
    if s.count(old) != count:
        sys.exit(f"introuvable ({s.count(old)}) : {old[:80]!r}")
    s = s.replace(old, new)

# 1. champ du dessin
rep("    u32 fp_bytes;              /* exact complete bytecode length, 0 = invalid */\n} D3D12DrawRecord;",
    "    u32 fp_bytes;              /* exact complete bytecode length, 0 = invalid */\n"
    "    /* fork: half a texel in a15 units (u, v) by which each 6-vertex quad's\n"
    "     * texture rectangle is pulled in (vf_wrap_vs), 0 = none. */\n"
    "    float uv_inset[2];\n} D3D12DrawRecord;")
# 2. table avec drapeaux
rep("typedef struct { uint64_t hash; u32 w, h; } NearestTex;",
    "typedef struct { uint64_t hash; u32 w, h; u32 flags; } NearestTex;   /* flags: 1 nearest, 2 quad inset */")
rep("""    static const NearestTex defaults[] = {
        { 0x7726B4869ECEE0ECull, 768, 768 },   /* US and EU English */
        { 0xF58B146B534288E3ull, 768, 768 },   /* EU French */
        { 0xEC0CF14D42A0FAB4ull, 768, 768 },   /* EU German */
        { 0x188C27260D8D88FEull, 768, 768 },   /* EU Italian */
        { 0x835B8A496BEFFCE4ull, 768, 768 },   /* EU Spanish */
    };
    s_nearest_n = 0;
    const char* e = getenv("CV_NEAREST_TEXTURES");
    if (e && !strcmp(e, "0")) { fprintf(stderr, "[NEAREST] off (CV_NEAREST_TEXTURES=0)\\n"); return; }
    for (size_t i = 0; i < sizeof defaults / sizeof defaults[0]; i++) s_nearest[s_nearest_n++] = defaults[i];
    while (e && *e && s_nearest_n < 32) {
        unsigned long long h = 0; unsigned w = 0, hh = 0; int n = 0;
        if (sscanf(e, "%llx:%ux%u%n", &h, &w, &hh, &n) == 3 && n > 0) {
            s_nearest[s_nearest_n].hash = h; s_nearest[s_nearest_n].w = w; s_nearest[s_nearest_n].h = hh; s_nearest_n++;
            e += n;
        } else break;
        while (*e == ',' || *e == ' ') e++;
    }
    fprintf(stderr, "[NEAREST] %d textures sampled at texel centres\\n", s_nearest_n);
}""",
"""    /* The inventory's atlases. Every quad is 6 vertices (two triangles)
     * whose texture rectangle ends exactly on its neighbour's texels: the
     * bilinear filter took in half of that neighbour (a dark separator
     * column, or across the wrap, the atlas's black last column), a thin
     * line at 4K at every joint. Pulling each quad's rectangle in by half a
     * texel (vf_wrap_vs) keeps the filtering and drops the bleed. Measured
     * with CV_NEAREST_DUMP on the inventory: coordinates are a15 / 4096. */
    static const NearestTex defaults[] = {
        { 0x7726B4869ECEE0ECull, 768, 768, 2 },    /* panels, US and EU English */
        { 0xF58B146B534288E3ull, 768, 768, 2 },    /* panels, EU French */
        { 0xEC0CF14D42A0FAB4ull, 768, 768, 2 },    /* panels, EU German */
        { 0x188C27260D8D88FEull, 768, 768, 2 },    /* panels, EU Italian */
        { 0x835B8A496BEFFCE4ull, 768, 768, 2 },    /* panels, EU Spanish */
        { 0x80825AC3566791AEull, 768, 768, 2 },    /* item icons and their blue boxes */
        { 0x0970338B235A8658ull, 768, 768, 2 },    /* item icons */
        { 0x7A9A1A1002AC8258ull, 768, 1024, 2 },   /* status panel pieces */
        { 0x59FBCA3A77575D6Eull, 384, 384, 2 },    /* small pieces */
        { 0x7B993BFC9B73DEF8ull, 768, 768, 2 },    /* background grid */
    };
    s_nearest_n = 0;
    const char* inset = getenv("CV_UV_INSET");
    if (!(inset && !strcmp(inset, "0")))
        for (size_t i = 0; i < sizeof defaults / sizeof defaults[0]; i++) s_nearest[s_nearest_n++] = defaults[i];
    /* CV_NEAREST_TEXTURES=<hash>:<w>x<h>,... : texel-centre sampling;
     * CV_UV_INSET_TEXTURES: more quad-inset textures. */
    for (int pass = 0; pass < 2; pass++) {
        const char* e = getenv(pass ? "CV_UV_INSET_TEXTURES" : "CV_NEAREST_TEXTURES");
        while (e && *e && s_nearest_n < 32) {
            unsigned long long h = 0; unsigned w = 0, hh = 0; int n = 0;
            if (sscanf(e, "%llx:%ux%u%n", &h, &w, &hh, &n) == 3 && n > 0) {
                s_nearest[s_nearest_n].hash = h; s_nearest[s_nearest_n].w = w; s_nearest[s_nearest_n].h = hh;
                s_nearest[s_nearest_n].flags = pass ? 2u : 1u; s_nearest_n++;
                e += n;
            } else break;
            while (*e == ',' || *e == ' ') e++;
        }
    }
    fprintf(stderr, "[NEAREST] %d listed textures (quad inset %s)\\n", s_nearest_n, vf_enabled() ? "on" : "needs RSX_GPU_VFETCH=1");
}""")
# 3. tex_nearest -> drapeaux
rep("static int tex_nearest(u32 off, u32 w, u32 h, u32 fmt)\n{", "static int tex_fork_flags(u32 off, u32 w, u32 h, u32 fmt)\n{")
rep("""    const uint64_t hash = texpack_hash(p, bytes, w, h, basef);
    int result = 0;
    for (int i = 0; i < s_nearest_n; i++) if (s_nearest[i].hash == hash) result = 1;""",
"""    const uint64_t hash = texpack_hash(p, bytes, w, h, basef);
    int result = 0;
    for (int i = 0; i < s_nearest_n; i++)
        if (s_nearest[i].hash == hash && s_nearest[i].w == w && s_nearest[i].h == h) result |= (int)s_nearest[i].flags;""")
rep("""    if (result) fprintf(stderr, "[NEAREST] texture %016llX at 0x%08X: texel-centre sampling\\n", (unsigned long long)hash, off);
    return result;
}""", """    if (result) fprintf(stderr, "[NEAREST] texture %016llX at 0x%08X: flags %d\\n", (unsigned long long)hash, off, result);
    return result;
}
static int tex_nearest(u32 off, u32 w, u32 h, u32 fmt) { return tex_fork_flags(off, w, h, fmt) & 1; }""")
# releve
rep("static int tex_nearest(u32 off, u32 w, u32 h, u32 fmt);\nstatic void nearest_dump(u32 ndraws)",
    "static int tex_fork_flags(u32 off, u32 w, u32 h, u32 fmt);\nstatic void nearest_dump(u32 fi, u32 ndraws)")
rep("            if (r->tex[u].set && !r->tex[u].cube && tex_nearest(r->tex[u].off, r->tex[u].w, r->tex[u].h, r->tex[u].fmt)) hit = 1;",
    "            if (r->tex[u].set && !r->tex[u].cube && tex_fork_flags(r->tex[u].off, r->tex[u].w, r->tex[u].h, r->tex[u].fmt)) hit = 1;")
rep("""            fprintf(f, "  t%d %ux%u fmt=%02X addr=%08X off=%08X hash=%016llX nearest=%d\\n", u, w, hh, bf, r->tex[u].addr,
                    r->tex[u].off, h, !r->tex[u].cube && tex_nearest(r->tex[u].off, w, hh, r->tex[u].fmt));""",
"""            fprintf(f, "  t%d %ux%u fmt=%02X addr=%08X off=%08X hash=%016llX flags=%d\\n", u, w, hh, bf, r->tex[u].addr,
                    r->tex[u].off, h, r->tex[u].cube ? 0 : tex_fork_flags(r->tex[u].off, w, hh, r->tex[u].fmt));""")
rep("""        fprintf(f, "op%03u n=%u topo=%u vs=%d rt=0x%08X %ux%u vp=%u,%u,%u,%u blend=%d\\n", d, r->vertex_count, r->topology,
                r->vs_idx, r->rt_off, r->rt_w, r->rt_h, r->vp_x, r->vp_y, r->vp_w, r->vp_h, r->blend);""",
"""        fprintf(f, "op%03u n=%u topo=%u vs=%d rt=0x%08X %ux%u vp=%u,%u,%u,%u blend=%d inset=%g,%g\\n", d, r->vertex_count, r->topology,
                r->vs_idx, r->rt_off, r->rt_w, r->rt_h, r->vp_x, r->vp_y, r->vp_w, r->vp_h, r->blend, r->uv_inset[0], r->uv_inset[1]);""")
rep("        for (u32 v = 0; v < r->vertex_count && v < 256; v++) {", "        for (u32 v = 0; v < r->vertex_count && v < 2048; v++) {")
rep("""    fclose(f);
    fprintf(stderr, "[NEAREST] draw dump written to %s\\n", path);""",
"""    fclose(f);
    fprintf(stderr, "[NEAREST] draw dump written to %s\\n", path);
    /* and the whole frame at full resolution (<RSX_CAP_DIR>/frame_99) */
    if (getenv("CV_NEAREST_DUMP_CAP")) rsx_capture_frame(fi, ndraws, 99);""")
rep("    nearest_dump(s_dbg_last_draws);", "    nearest_dump(fi, s_dbg_last_draws);")
# 4. vp_record_cb
rep("""        /* fork: rsx_texaddr[u].z bit 9 and .w + 16: sample this unit at texel
         * centres (tex_nearest). 2D textures only. */
        if (dr)""",
"""        /* fork: quad inset for unit 0 (vf_wrap_vs), half a texel in a15
         * units, the inventory's texture coordinates being a15 / 4096. */
        if (dr) {
            D3D12DrawRecord* w = (D3D12DrawRecord*)dr;
            w->uv_inset[0] = w->uv_inset[1] = 0.0f;
            if (vf_enabled() && dr->tex[0].set && !dr->tex[0].cube && dr->tex[0].w && dr->tex[0].h &&
                (tex_fork_flags(dr->tex[0].off, dr->tex[0].w, dr->tex[0].h, dr->tex[0].fmt) & 2)) {
                w->uv_inset[0] = 2048.0f / (float)dr->tex[0].w;
                w->uv_inset[1] = 2048.0f / (float)dr->tex[0].h;
            }
        }
        /* fork: rsx_texaddr[u].z bit 9 and .w + 16: sample this unit at texel
         * centres (tex_nearest). 2D textures only. */
        if (dr)""")
# 5. signature racine
rep("""        rp[5].Constants.ShaderRegister = 2;
        rp[5].Constants.Num32BitValues = 1;""", """        rp[5].Constants.ShaderRegister = 2;
        rp[5].Constants.Num32BitValues = 3;   /* fork: + quad inset u, v */""")
# 6. dessin
rep("""                      s_d3d.cmd_list->lpVtbl->SetGraphicsRoot32BitConstant(s_d3d.cmd_list, 5,
                          dr->vb_byte_offset / 256, 0);""",
"""                      { UINT k[3] = { dr->vb_byte_offset / 256, 0, 0 };
                        /* fork: quad inset only on whole 6-vertex quads, unbatched */
                        if ((dr->uv_inset[0] > 0.0f || dr->uv_inset[1] > 0.0f) && dr->topology == RSX_TOPOLOGY_TRIANGLES &&
                            draw_vertices == dr->vertex_count && dr->vertex_count % 6u == 0u) {
                            memcpy(&k[1], &dr->uv_inset[0], 4); memcpy(&k[2], &dr->uv_inset[1], 4);
                        }
                        s_d3d.cmd_list->lpVtbl->SetGraphicsRoot32BitConstants(s_d3d.cmd_list, 5, 3, k, 0); }""")
# 7. shader
rep('''        "cbuffer VFDraw : register(b2) { uint vf_first; };\\n"''',
    '''        "cbuffer VFDraw : register(b2) { uint vf_first; float vf_inset_u; float vf_inset_v; };\\n"''')
rep('''        "#if VF_POSE_ENABLED\\n"
        "    input.a0=vf_pose_position(vf_first+vf_vid,input.a0);\\n"
        "#endif\\n"
        "    return vf_main(input);\\n"''',
'''        "    if (vf_inset_u > 0.0 || vf_inset_v > 0.0) {\\n"
        "        uint qb = vf_vid - vf_vid % 6u; float2 lo = float2(1e30, 1e30), hi = float2(-1e30, -1e30);\\n"
        "        [unroll] for (uint qk = 0u; qk < 6u; qk++) { uint2 qr = vf_buf.Load2((vf_first + qb + qk) * 8u);\\n"
        "            float2 qt = vf_fetch(qr.y, 15u, qr.x).xy; lo = min(lo, qt); hi = max(hi, qt); }\\n"
        "        float2 ins = float2(vf_inset_u, vf_inset_v); float2 t = input.a15.xy;\\n"
        "        [unroll] for (uint c = 0u; c < 2u; c++) if (hi[c] - lo[c] >= 2.0 * ins[c]) {\\n"
        "            if (t[c] <= lo[c]) t[c] += ins[c]; else if (t[c] >= hi[c]) t[c] -= ins[c]; }\\n"
        "        input.a15.xy = t;\\n"
        "    }\\n"
        "#if VF_POSE_ENABLED\\n"
        "    input.a0=vf_pose_position(vf_first+vf_vid,input.a0);\\n"
        "#endif\\n"
        "    return vf_main(input);\\n"''')
open(p, 'wb').write(s.encode('latin-1'))
print('ok')
