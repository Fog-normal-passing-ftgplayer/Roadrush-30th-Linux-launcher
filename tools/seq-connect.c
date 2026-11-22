/* seq-connect: 把 Wine 的 MIDI 输出端口桥接到 fluidsynth 的合成器输入端口
 * 用法: seq-connect [srcNameSubstr] [dstNameSubstr]   (默认 "WINE" / "FLUID")
 * 反复扫描 ALSA sequencer，端口一出现就建立订阅；不会因端口消失而退出。
 */
#define _GNU_SOURCE
#include <alsa/asoundlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int find_ports(snd_seq_t *seq, const char *needle, int want_read, int *out_c, int *out_p)
{
    snd_seq_client_info_t *ci; snd_seq_port_info_t *pi; int found = 0;
    snd_seq_client_info_alloca(&ci); snd_seq_port_info_alloca(&pi);
    snd_seq_client_info_set_client(ci, -1);
    while (snd_seq_query_next_client(seq, ci) >= 0) {
        const char *name = snd_seq_client_info_get_name(ci);
        if (!name || !strstr(name, needle)) continue;
        int c = snd_seq_client_info_get_client(ci);
        snd_seq_port_info_set_client(pi, c);
        snd_seq_port_info_set_port(pi, -1);
        while (snd_seq_query_next_port(seq, pi) >= 0) {
            unsigned caps = snd_seq_port_info_get_capability(pi);
            if (want_read ? (caps & SND_SEQ_PORT_CAP_READ) : (caps & SND_SEQ_PORT_CAP_WRITE)) {
                out_c[found] = c;
                out_p[found] = snd_seq_port_info_get_port(pi);
                if (++found >= 8) return found;
                break;   /* 每个 client 只用第一个合适端口 */
            }
        }
    }
    return found;
}

int main(int argc, char **argv)
{
    const char *src = argc > 1 ? argv[1] : "WINE";
    const char *dst = argc > 2 ? argv[2] : "FLUID";
    snd_seq_t *seq;
    if (snd_seq_open(&seq, "default", SND_SEQ_OPEN_DUPLEX, 0) < 0) {
        fprintf(stderr, "seq-connect: 打不开 ALSA sequencer\n"); return 1;
    }
    snd_seq_set_client_name(seq, "rr-midi-bridge");
    int myport = snd_seq_create_simple_port(seq, "bridge",
        SND_SEQ_PORT_CAP_READ | SND_SEQ_PORT_CAP_WRITE | SND_SEQ_PORT_CAP_SUBS_READ
        | SND_SEQ_PORT_CAP_SUBS_WRITE, SND_SEQ_PORT_TYPE_MIDI_GENERIC);
    if (myport < 0) { fprintf(stderr, "seq-connect: 建端口失败\n"); return 1; }

    for (;;) {
        int sc[8], sp[8], dc[8], dp[8];
        int ns = find_ports(seq, src, 1, sc, sp);   /* 源：可读 */
        int nd = find_ports(seq, dst, 0, dc, dp);   /* 目标：可写 */
        for (int i = 0; i < ns; i++)
            for (int j = 0; j < nd; j++) {
                if (snd_seq_connect_from(seq, myport, sc[i], sp[i]) < 0) { /* 可能已连 */ }
                if (snd_seq_connect_to(seq, myport, dc[j], dp[j]) < 0) { /* 可能已连 */ }
            }
        sleep(2);
    }
    return 0;
}
