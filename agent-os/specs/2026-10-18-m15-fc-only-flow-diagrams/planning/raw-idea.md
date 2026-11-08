# Raw Idea

tamam şimdi iki adet akış şemasını değiştirmeden sadece vision tarafından yazılanları
  kaldır sadece benim yapacağım bana ne gelip ta pwm e nasıl gidiyor ya benim kısmın yani
  benim çalışma alanım sadece fc kısmı o yüzden o tarafları kaldırılaım ona göre düzeleme yapalım

## Context note

This follows the previous spec `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/`, which produced two Mermaid flowcharts: `diagrams/01-ust-seviye-akis.md` (high-level) and `diagrams/02-px4-detayli-akis.md` (detailed PX4, blocks A-D). The user's work area is only the flight controller (FC). They want FC-only versions of both diagrams: remove the Vision / Raspberry Pi side (camera, detection, pixel->camera->body LOS, Pi-side MAVLink sending), starting from what arrives at the FC and going all the way down to PWM output, without otherwise changing the diagrams.
