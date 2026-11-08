# Şema 1 — Hedef Takip Uçuş Modu: Üst Seviye Akış

> **Not:** Bu şema FC'ye özel olarak güncellendi, bkz. `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`. Önceki spec'in `spec.md`, `tasks.md` ve `implementation/` metinleri Pi'yi ve Şema 2'nin 5 adımlı (D) akışını anlatmaya devam eder.

FC'ye MAVLink ile body FRD LOS gelir (montaj açısı dahil), FC bunu PWM'e kadar işler. Pixhawk 6C üzerinde çalışan tez uçuş modu, mod aktifken gelen mesajı kontrol eder, LOS'u araç yönelimi ve irtifayla hedefin yerel NED konumuna çevirir (geolocation), hedefi kestirir ve guidance ile istenen hızı ve yaw'u üretir. Hedef bir süre görünmezse araç yerinde bekler, süre dolunca Hold'a geçer. İsteği PX4'ün kendi kontrolcüleri motor karıştırmaya ve MAIN çıkışındaki PWM sinyaline kadar taşır, ESC'ler motorları döndürür. Hesap düz dünya kabulüyle yerel NED çerçevesinde yapılır, küresel koordinat dönüşümü yoktur.

- Üslup rehberi: [referans görsel](../planning/visuals/WhatsApp%20Image%202026-09-26%20at%2000.07.13.jpeg) (`../planning/visuals/WhatsApp Image 2026-09-26 at 00.07.13.jpeg`). Görsel birebir kopyalanmadı, yalnızca şekil dili alındı.
- Lejant: paralelkenar = girdi, yuvarlak köşeli kutu = işlem, eşkenar dörtgen = karar, kesik çizgili kutu = açık konu (TBD). Ok üzerindeki yazı, bir adımdan sonrakine geçen bilgidir.
- Guidance yasasının ayrıntısı bu şemada yoktur. Bkz. `/home/yusuf/Desktop/guidance-yasalari.md`. PX4'e özel ayrıntılar `02-px4-detayli-akis.md` dosyasındadır. Her kutunun Şema 2 karşılığı, o dosyadaki (B) bloğunun "Şema 1 ile karşılık" tablosundadır.

```mermaid
flowchart TB
    inMode[/"Pilot / QGC mod seçimi"/]
    icdMsg[/"Body FRD LOS (montaj açısı dahil), MAVLink ile gelir (ICD TBD)"/]

    subgraph fcBox ["Pixhawk 6C / PX4 — Tez uçuş modu"]
        direction TB
        fcEnter("Moda giriş")
        fcExit("Mod anahtarıyla çıkış")
        fcModeQ{"Mod aktif mi?"}
        fcIdle("Hesap yapılmaz")
        fcMsgQ{"Gelen mesaj geçerli mi?"}
        fcDrop("Örnek atılır")
        fcSeenQ{"Hedef görünüyor mu?"}
        fcWait("Yerinde bekle (son konum ve yön tutulur)")
        fcHold("Süre dolunca Hold")
        inAtt[/"UAV Roll / Pitch / Yaw"/]
        inAlt[/"İrtifa (baro / EKF) — TBD"/]
        inPos[/"UAV yerel NED konumu"/]
        fcNedLos("LOS'u yere göre yöne çevir (NED)")
        fcRange("Aşağı açı ve eğik mesafe")
        fcTargetNed("Hedefin yerel NED konumu")
        fcEstimate("Hedef kestirimi (konum/hız)")
        subgraph fcGuidBox ["Guidance: istenen durum"]
            direction TB
            fcGuidPos("İstenen konum / takip mesafesi")
            fcGuidVel("İstenen hız")
            fcGuidYaw("Yaw hedefe bakar")
            fcGuidLim("Hız ve irtifa sınırları")
        end
        subgraph fcCtlBox ["PX4 kontrolcüleri"]
            direction TB
            fcPosCtl("Konum kontrolü")
            fcAttCtl("Tutum kontrolü")
            fcRateCtl("Açısal hız kontrolü")
            fcMix("Motor karıştırma")
        end
        fcPwm("PWM sinyali (MAIN çıkışı)")
    end

    fcEsc("ESC")
    fcMotors("Motorlar")
    fcFollow("Araç hedefi takip eder")

    inMode -- "takip modu seçilir" --> fcEnter
    inMode -- "başka mod seçilir (RC mod anahtarı veya QGC)" --> fcExit
    fcEnter --> fcModeQ
    fcExit --> fcModeQ
    fcModeQ -- "evet" --> fcMsgQ
    fcModeQ -- "hayır" --> fcIdle
    icdMsg --> fcMsgQ
    fcMsgQ -- "evet: doğru ad, sayılar geçerli, birim vektör, mesaj taze" --> fcNedLos
    fcMsgQ -- "hayır" --> fcDrop
    fcDrop --> fcSeenQ
    fcSeenQ -- "hayır" --> fcWait
    fcWait --> fcHold
    fcSeenQ -- "evet: son ölçümle tahmin sürer" --> fcEstimate
    fcNedLos --> fcRange
    fcRange --> fcTargetNed
    fcTargetNed --> fcEstimate
    fcEstimate --> fcGuidPos
    fcGuidPos --> fcGuidVel
    fcGuidVel --> fcGuidYaw
    fcGuidYaw --> fcGuidLim
    fcGuidLim -- "istenen hız ve yaw" --> fcPosCtl
    fcPosCtl -- "istenen eğim ve itki" --> fcAttCtl
    fcAttCtl -- "istenen dönüş hızı" --> fcRateCtl
    fcRateCtl -- "istenen dönme kuvveti ve itki" --> fcMix
    fcMix -- "her motorun payı" --> fcPwm
    fcPwm --> fcEsc
    fcEsc --> fcMotors
    fcMotors --> fcFollow

    inAtt --> fcNedLos
    inAlt --> fcRange
    inPos --> fcTargetNed

    classDef input fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000
    classDef process fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000
    classDef decision fill:#ffffff,stroke:#000000,stroke-width:1.5px,color:#000000
    classDef tbd fill:#ffffff,stroke:#000000,stroke-width:1.5px,stroke-dasharray: 5 5,color:#000000
    class inMode,inAtt,inPos input
    class fcEnter,fcExit,fcIdle,fcDrop,fcWait,fcHold,fcNedLos,fcRange,fcTargetNed,fcEstimate process
    class fcGuidPos,fcGuidVel,fcGuidYaw,fcGuidLim,fcPosCtl,fcAttCtl,fcRateCtl,fcMix,fcPwm,fcEsc,fcMotors,fcFollow process
    class fcModeQ,fcMsgQ,fcSeenQ decision
    class icdMsg,inAlt tbd
    style fcBox fill:#f7f7f7,stroke:#7f7f7f
    style fcGuidBox fill:#ffffff,stroke:#7f7f7f
    style fcCtlBox fill:#ffffff,stroke:#7f7f7f
    linkStyle default stroke:#4472c4,stroke-width:1.5px
```
