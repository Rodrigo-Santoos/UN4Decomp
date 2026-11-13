// UN4Decomp: reproduz um gsdump_*.bin gravado pelo jogo (ver un4_gsdump.h) e salva as imagens.
// Uso: un4_gsreplay dump.bin saida_prefixo [--draws N] (para depois de N records de desenho, para bisseccao)
#include "un4_profile.h"
#include "runtime/gs/gs_frontend.h"
#include "runtime/gs/un4_gsdump.h"
#include "runtime/ps2_memory.h"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

static bool writePPM(const std::string &path, const std::vector<uint8_t> &px, uint32_t w, uint32_t h)
{
    FILE *f = std::fopen(path.c_str(), "wb");
    if (!f) return false;
    std::fprintf(f, "P6\n%u %u\n255\n", w, h);
    for (size_t i = 0; i < size_t(w) * h; ++i)
        std::fwrite(&px[i * 4], 1, 3, f);
    std::fclose(f);
    return true;
}

int main(int argc, char **argv)
{
    if (argc < 3) { std::fprintf(stderr, "uso: %s dump.bin prefixo [--recs N] [--quiet]\n", argv[0]); return 1; }
    long maxRecs = -1;
    for (int i = 3; i < argc; ++i)
        if (!std::strcmp(argv[i], "--recs") && i + 1 < argc) maxRecs = std::atol(argv[++i]);
    std::ifstream in(argv[1], std::ios::binary);
    std::vector<uint8_t> file((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (file.size() < 16 || std::memcmp(file.data(), "UN4GSDMP", 8)) { std::fprintf(stderr, "arquivo invalido\n"); return 1; }
    const uint8_t *p = file.data() + 8; size_t left = file.size() - 8;
    uint32_t ver = 0, stateSize = 0, vramSize = 0;
    un4gsdump::get(p, left, &ver, 4);
    un4gsdump::get(p, left, &stateSize, 4);
    const uint8_t *state = p; p += stateSize; left -= stateSize;
    un4gsdump::get(p, left, &vramSize, 4);
    const uint8_t *vramData = p; p += vramSize; left -= vramSize;

    uint8_t *vram = new uint8_t[vramSize];
    std::memcpy(vram, vramData, vramSize);
    static GSRegisters regs{};
    GS gs;
    gs.init(vram, vramSize, &regs);
    gs.un4LoadState(state, stateSize);
    std::memcpy(vram, vramData, vramSize);
    if (const char *cz = std::getenv("UN4_REPLAY_CLEAR"))
    {
        // "addr_hex,bytes_hex[;...]" zera regioes da VRAM antes de reproduzir
        const char *q = cz;
        while (*q) { unsigned a = 0, n = 0; int used = 0; if (std::sscanf(q, "%x,%x%n", &a, &n, &used) != 2) break;
            if (a < vramSize) std::memset(vram + a, 0, std::min<size_t>(n, vramSize - a)); q += used; if (*q == ';') ++q; }
    }

    uint32_t frame = 0; long recs = 0;
    // UN4_REPLAY_PIXELS="x,y;x,y" acompanha pixels do FB de desenho (fbp/fbw em UN4_REPLAY_FB="fbp,fbw", padrao 0,8)
    std::vector<std::pair<int,int>> watch;
    if (const char *w = std::getenv("UN4_REPLAY_PIXELS"))
    {
        const char *q = w;
        while (*q) { int x = 0, y = 0, n = 0; if (std::sscanf(q, "%d,%d%n", &x, &y, &n) != 2) break; watch.push_back({x, y}); q += n; if (*q == ';') ++q; }
    }
    uint32_t fbBase = 0, fbW = 8;
    if (const char *fb = std::getenv("UN4_REPLAY_FB")) std::sscanf(fb, "%u,%u", &fbBase, &fbW);
    std::vector<uint32_t> lastPix(watch.size(), 0xFFFFFFFFu);
    if (std::getenv("UN4_REPLAY_DRAWLOG")) un4prof::gsCaptureBudget().store(100000000);
    long fbDumpAt = -1; if (const char *v = std::getenv("UN4_REPLAY_FBDUMP_AT")) fbDumpAt = std::atol(v);
    auto dumpFb = [&](const char *name) {
        std::vector<uint8_t> px(size_t(fbW) * 64 * 448 * 4);
        const uint32_t W = fbW * 64;
        for (uint32_t y = 0; y < 448; ++y) for (uint32_t x = 0; x < W; ++x) {
            const uint32_t v = gs.ReadVram(0, fbBase, fbW, x, y);
            std::memcpy(&px[(size_t(y) * W + x) * 4], &v, 4);
        }
        writePPM(name, px, W, 448);
        std::printf("fb salvo %s\n", name);
    };
    uint64_t gifBytes = 0, nGif = 0, nUp = 0, nReg = 0;
    auto t0 = std::chrono::steady_clock::now();
    const int loops = std::getenv("UN4_REPLAY_PROF") ? std::atoi(std::getenv("UN4_REPLAY_PROF")) : 0;
    if (loops > 0) un4prof::cpu::start();
    double gsSeconds = 0;
    auto present = [&](const char *tag) {
        gs.latchHostPresentationFrame();
        std::vector<uint8_t> px; uint32_t w = 0, h = 0, dfbp = 0, sfbp = 0; bool pref = false;
        if (gs.copyLatchedHostPresentationFrame(px, w, h, &dfbp, &sfbp, &pref))
        {
            char name[256]; std::snprintf(name, sizeof(name), "%s_%02u%s.ppm", argv[2], frame, tag);
            writePPM(name, px, w, h);
            std::printf("quadro %u: %ux%u dispfbp=%x srcfbp=%x pref=%d -> %s\n", frame, w, h, dfbp, sfbp, int(pref), name);
        }
        ++frame;
    };
    const uint8_t *recStart = p; const size_t recLeft = left;
    for (int iter = 0; iter < std::max(1, loops); ++iter)
    {
    if (iter > 0)
    {
        p = recStart; left = recLeft; frame = 0; recs = 0;
        std::memcpy(vram, vramData, vramSize);
        gs.un4LoadState(state, stateSize);
        std::memcpy(vram, vramData, vramSize);
    }
    const bool lastIter = iter + 1 >= std::max(1, loops);
    while (left >= 8)
    {
        uint32_t kind = 0, size = 0;
        un4gsdump::get(p, left, &kind, 4);
        un4gsdump::get(p, left, &size, 4);
        if (kind == un4gsdump::kEnd) break;
        if (size > left) { std::fprintf(stderr, "record truncado\n"); break; }
        const uint8_t *d = p; p += size; left -= size;
        if (maxRecs >= 0 && recs >= maxRecs && kind != un4gsdump::kVsync) { continue; }
        auto a = std::chrono::steady_clock::now();
        switch (kind)
        {
        case un4gsdump::kVsync: {
            uint64_t v[8]; std::memcpy(v, d, sizeof(v));
            regs.pmode = v[0]; regs.smode2 = v[1]; regs.dispfb1 = v[2]; regs.display1 = v[3];
            regs.dispfb2 = v[4]; regs.display2 = v[5]; regs.bgcolor = v[6]; regs.vsyncTick.store(v[7]);
            if (lastIter) present("");
            continue;
        }
        case un4gsdump::kGif: gs.processGIFPacket(d, size); ++nGif; gifBytes += size; break;
        case un4gsdump::kPacked: if (!gs.processNativePackedGIFPacket(d, size)) std::fprintf(stderr, "packed falhou\n"); ++nGif; gifBytes += size; break;
        case un4gsdump::kUpload: { uint64_t r[4]; std::memcpy(r, d, 32); gs.uploadImageNative(r[0], r[1], r[2], r[3], size > 32 ? d + 32 : nullptr, size - 32); ++nUp; gifBytes += size; break; }
        case un4gsdump::kReg: { uint64_t r[2]; std::memcpy(r, d, 16); gs.writeRegister(uint8_t(r[0]), r[1]); ++nReg; break; }
        case un4gsdump::kClear: { uint32_t r[2]; std::memcpy(r, d, 8); if (r[0] == 0xFFFFFFFFu) gs.clearActiveFramebuffer(r[1]); else gs.clearFramebufferContext(r[0], r[1]); break; }
        case un4gsdump::kWriteVram: { uint32_t r[6]; std::memcpy(r, d, 24); gs.WriteVram(r[0], r[1], r[2], r[3], r[4], r[5]); break; }
        default: std::fprintf(stderr, "record desconhecido %u\n", kind); break;
        }
        gsSeconds += std::chrono::duration<double>(std::chrono::steady_clock::now() - a).count();
        for (size_t i = 0; i < watch.size(); ++i)
        {
            const uint32_t v = gs.ReadVram(0, fbBase, fbW, watch[i].first, watch[i].second);
            if (v != lastPix[i]) { std::printf("[pix] rec=%ld (%d,%d) %08x -> %08x\n", recs, watch[i].first, watch[i].second, lastPix[i], v); std::fflush(stdout); lastPix[i] = v; }
        }
        if (std::getenv("UN4_REPLAY_DRAWLOG")) { std::fprintf(stderr, "[rec] %ld fim kind=%u size=%u\n", recs, kind, size); }
        if (recs == fbDumpAt) { char nm[256]; std::snprintf(nm, sizeof(nm), "%s_fb_rec%ld.ppm", argv[2], recs); dumpFb(nm); }
        ++recs;
    }
    } // iter
    present("_fim");
    if (loops > 0) un4prof::cpu::dump();
    if (const char *vo = std::getenv("UN4_REPLAY_VRAM_OUT"))
    {
        if (FILE *f = std::fopen(vo, "wb")) { std::fwrite(vram, 1, vramSize, f); std::fclose(f); }
    }
    std::printf("records=%ld gif=%llu uploads=%llu regs=%llu bytes=%llu tempoGS=%.3fs total=%.3fs\n", recs,
                (unsigned long long)nGif, (unsigned long long)nUp, (unsigned long long)nReg, (unsigned long long)gifBytes,
                gsSeconds, std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
    return 0;
}
