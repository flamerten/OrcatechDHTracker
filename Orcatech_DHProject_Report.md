# Orcatech DH Project Report

National University Of Singapore, Residential College 4

Done by:
- Yow Keng Yee Samuel (Class of 2024)
- Manzel Joseph Seet (Class of 2023)

Supervised by:
- Prof Naviyn Prabhu Balakrishnan

## Rationale

This project was started in AY2021/2022 Sem 2 when the Dinning Hall capacity was reduced due to Covid-19 Safe Management Measures. As the Dinning Hall could get quite crowded with long queues, we proposed the idea of utlising sensors at the doors of the dinning hall to track people coming into and out of the Dinning Hall so as to calculate the current number of people at any point in time. This would allows residents to make informed decsions on when to come down to get their food.


## List of Items Purchased
- VLX53L0X Laser Ranging Time Of Flight Sensor 
- VL53l1X Laser Ranging Time Of Flight Sensor
- Generic Dual USB Charger 
- Generic MircoUSB Cable
- ESP32 Dev Kit
- Raspberry Pi 3B
- High gain Wireless USB Adaptor TP Link [shoppee](https://shopee.sg/TP-Link-TL-WN722N-150-Mbps-High-Gain-Wireless-USB-Adapter-White-TPLink-i.101600.2161518348)
- [JLCPCB](https://jlcpcb.com/) - PCB Printing Service

## Relevant Links
- VL53L0X Laser Ranging Time Of Flight Sensor
    - Github [Library](https://github.com/adafruit/Adafruit_VL53L0X) 
    - Adafruit [Tutorial](https://learn.adafruit.com/adafruit-vl53l0x-micro-lidar-distance-sensor-breakout)
- ESP32
    - Over The Air Update (OTA) [Tutorial](https://randomnerdtutorials.com/esp32-over-the-air-ota-programming/)


## Fabrication and Installation

<img src="src/PCB.jpg" width="400"/>

[EasyEDA](https://easyeda.com/) was used to design the PCB, which contained the ESP32s and the VLX distance sensors. This was sent over to JLCPCB to be printed. However, the ESP32 did not fit the PCB exactly. Hence, the base of female pin headers was bent and sodlered on top of the through holes.

<img src="src/3Dprints.jpg" width="400"/>

For the casing, PLA filament with a 3D printer was used to prototype various methods of encasing the PCB. We initially tried using friction fitting but it was hard to get an accurate fit, and we realised it might encourage tampering as any resident coule remove a friction fit. Hence, our final iteration used screws to secure the cover.

<img src="src/Mounted.jpg" width="400"/>

The casing was mounted on to the pillars of the Dinning Hall using mounting tape. From some initial testing, we made some observations, which can be improved upon during the next iteration
- Mounting Tape is quite permanant and when taken out, pain is removed as well.
- The cover had cut as it seemed to block the VLX sensor's line of vision.
- One of the ESP32s were damanaged when the USB port broke off. We believe someone accidentally presed against it leading to the USB port being removed from the ESP32 board. Hence, that board needed to be swapped out. As such, future iterations need to consider such a scenario.

