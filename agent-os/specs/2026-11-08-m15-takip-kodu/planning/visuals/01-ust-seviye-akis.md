# Şema 1 — AUTO FOLLOW Uçuş Modu: Üst Seviye Akış

> **Güncelleme notu (2026-11-09):** Bu dosya, eski taslak `agent-os/specs/2026-10-15-m15-target-follow-flight-mode/diagrams/01-ust-seviye-akis.md`'nin kopyasıdır ve bu spec'in kararlarına göre güncellendi (kullanıcı onayı, `requirements.md` §11). Kararlaşan TBD'ler kararla değiştirildi, eski taslak adlar (`tez_follow`, `TEZ_FOL_*`, `TEZ_LOS`) AUTO FOLLOW / `auto_follow` / `AF_*` / `AF_LOS` oldu, masaüstü dosyası bağlantısı rapora çevrildi. **Asıl şema eski klasörde değişmeden durur.**
>
> Eski not (tarihsel): Bu şema FC'ye özel olarak güncellendi, bkz. `agent-os/specs/2026-10-18-m15-fc-only-flow-diagrams/`.

FC'ye MAVLink `DEBUG_FLOAT_ARRAY` (`name = AF_LOS`) ile body FRD LOS gelir (montaj açısı dahil), FC bunu PWM'e kadar işler. Pixhawk 6C üzerinde çalışan **AUTO FOLLOW** uçuş modu (`auto_follow` modülü, 50 Hz), mod aktifken gelen mesajı kontrol eder, LOS'u araç yönelimi ve yükseklik farkıyla hedefin yerel NED konumuna çevirir (geolocation), hedefi alpha-beta filtresiyle kestirir ve hız tabanlı guidance ile istenen yatay hızı ve yaw'u üretir. Hedef `AF_DATA_TOUT` boyunca görünmezse araç yerinde bekler, `AF_LOST_T` dolunca Hold'a geçer. İsteği (`trajectory_setpoint`) PX4'ün kendi kontrolcüleri motor karıştırmaya ve MAIN çıkışındaki PWM sinyaline kadar taşır, ESC'ler motorları döndürür. Hesap düz dünya kabulüyle yerel NED çerçevesinde yapılır, küresel koordinat dönüşümü yoktur.

- Üslup rehberi: [referans görsel](../../../2026-10-15-m15-target-follow-flight-mode/planning/visuals/WhatsApp%20Image%202026-09-26%20at%2000.07.13.jpeg) (eski taslak klasöründe). Görsel birebir kopyalanmadı, yalnızca şekil dili alındı.
- Lejant: paralelkenar = girdi, yuvarlak köşeli kutu = işlem, eşkenar dörtgen = karar, kesik çizgili kutu = açık konu (TBD). Ok üzerindeki yazı, bir adımdan sonrakine geçen bilgidir.
- Guidance yasasının ayrıntısı ve sayısal örnek: [`rapor.md`](../../rapor.md) (Bölüm 4.5) ve `spec.md`. PX4'e özel ayrıntılar `02-px4-detayli-akis.md` dosyasındadır. Her kutunun Şema 2 karşılığı, o dosyadaki (B) bloğunun "Şema 1 ile karşılık" tablosundadır.
- Girdi biçimi bir **varsayımdır** (V2); kesin biçim ortak ICD'de (yol haritası 3–5) belirlenecek. Açık kalan TBD: ICD zaman biçimi.

```mermaid
flowchart TB
    inMode[/"Pilot / QGC mod seçimi"/]
    icdMsg[/"Body FRD LOS (montaj açısı dahil), MAVLink DEBUG_FLOAT_ARRAY ile gelir<br/>name = AF_LOS (varsayım, ICD m3–5 bekleniyor)<br/>data[0..2] LOS x,y,z · data[3] yaş (ms) · data[4] sıra no · data[5] hedef var/yok"/]
    icdTime("TBD: ICD zaman biçimi<br/>varsayım: yaş (ms); kesin biçim ortak ICD'de")

    subgraph fcBox ["Pixhawk 6C / PX4 — AUTO FOLLOW (auto_follow modülü, 50 Hz)"]
        direction TB
        fcEnter("Moda giriş (giriş irtifası saklanır)")
        fcExit("Mod anahtarıyla çıkış")
        fcModeQ{"Mod aktif mi?"}
        fcIdle("PX4'e setpoint gönderilmez<br/>(veri işlenmeye devam edebilir)")
        fcMsgQ{"Gelen mesaj geçerli mi?"}
        fcDrop("Örnek atılır, nedeniyle sayılır")
        fcSeenQ{"Hedef görünüyor mu?"}
        fcWait("KAYIP_BEKLE: yerinde bekle<br/>(konum tutulur, hız 0, son yaw)")
        fcHold("AF_LOST_T (1.0 s) dolunca Hold isteği<br/>takibe kendiliğinden dönülmez")
        inAtt[/"UAV Roll / Pitch / Yaw (vehicle_attitude)"/]
        inAlt[/"Drone yüksekliği = -vehicle_local_position.z<br/>yükseklik farkı = -z - AF_GND_OFS - AF_TGT_HGT"/]
        inPos[/"UAV yerel NED konumu"/]
        fcNedLos("LOS'u yere göre yöne çevir (NED)")
        fcRange("Aşağı açı ve yatay mesafe<br/>açı ≥ AF_MIN_DEP, mesafe ≤ AF_MAX_RNG değilse örnek atılır")
        fcTargetNed("Hedefin yerel NED konumu")
        fcEstimate("Alpha-beta filtresi (AF_ALPHA, AF_BETA)<br/>hedef konumu + hızı")
        subgraph fcGuidBox ["Guidance: istenen durum (hız tabanlı; nihai yasa m13)"]
            direction TB
            fcGuidPos("İstenen mesafe = yükseklik farkı / tan(AF_TRK_ANG)")
            fcGuidVel("İstenen yatay hız = AF_K_FF · hedef hızı<br/>+ AF_K_DIST · (mesafe - istenen mesafe), hedef yönünde")
            fcGuidYaw("Yaw hedefe bakar (mutlak)<br/>mesafe #60; AF_YAW_MIN_D ise yaw sabit")
            fcGuidLim("Hız ≤ AF_VEL_MAX, değişim ≤ AF_ACC_MAX<br/>irtifa: giriş irtifası sabit")
        end
        subgraph fcCtlBox ["PX4 kontrolcüleri"]
            direction TB
            fcPosCtl("Konum kontrolü")
            fcAttCtl("Tutum kontrolü")
            fcRateCtl("Açısal hız kontrolü")
            fcMix("Motor karıştırma")
        end
        fcPwm("PWM sinyali (MAIN çıkışı)")
        fcLog("auto_follow_status log mesajı<br/>(her çevrim, her logda kaydedilir)")
    end

    fcEsc("ESC")
    fcMotors("Motorlar")
    fcFollow("Araç hedefi takip eder")

    inMode -- "AUTO FOLLOW seçilir" --> fcEnter
    inMode -- "başka mod seçilir (RC mod anahtarı veya QGC)" --> fcExit
    fcEnter --> fcModeQ
    fcExit --> fcModeQ
    fcModeQ -- "evet" --> fcMsgQ
    fcModeQ -- "hayır" --> fcIdle
    icdMsg --> fcMsgQ
    icdMsg -.- icdTime
    fcMsgQ -- "evet: ad AF_LOS, sayılar sonlu, birim vektör (±AF_NORM_TOL),<br/>sıra no artıyor, yaş #60; AF_DATA_TOUT, hedef var, konum geçerli" --> fcNedLos
    fcMsgQ -- "hayır" --> fcDrop
    fcDrop --> fcSeenQ
    fcSeenQ -- "hayır: AF_DATA_TOUT (0.5 s) geçerli veri yok<br/>veya Pi #quot;hedef yok#quot; dedi" --> fcWait
    fcWait --> fcHold
    fcSeenQ -- "evet: son ölçümle tahmin sürer" --> fcEstimate
    fcNedLos --> fcRange
    fcRange --> fcTargetNed
    fcTargetNed --> fcEstimate
    fcEstimate --> fcGuidPos
    fcGuidPos --> fcGuidVel
    fcGuidVel --> fcGuidYaw
    fcGuidYaw --> fcGuidLim
    fcGuidLim -- "trajectory_setpoint: yatay hız + irtifa + mutlak yaw" --> fcPosCtl
    fcGuidLim -.- fcLog
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
    class inMode,inAtt,inPos,inAlt,icdMsg input
    class fcEnter,fcExit,fcIdle,fcDrop,fcWait,fcHold,fcNedLos,fcRange,fcTargetNed,fcEstimate process
    class fcGuidPos,fcGuidVel,fcGuidYaw,fcGuidLim,fcPosCtl,fcAttCtl,fcRateCtl,fcMix,fcPwm,fcEsc,fcMotors,fcFollow,fcLog process
    class fcModeQ,fcMsgQ,fcSeenQ decision
    class icdTime tbd
    style fcBox fill:#f7f7f7,stroke:#7f7f7f
    style fcGuidBox fill:#ffffff,stroke:#7f7f7f
    style fcCtlBox fill:#ffffff,stroke:#7f7f7f
    linkStyle default stroke:#4472c4,stroke-width:1.5px
```
