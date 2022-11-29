// Wemos® D1 R32
// Board: ESP32 Dev Module

#include "EspMQTTClient.h"
#include "Adafruit_VL53L0X.h"
#include <Wire.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <AsyncElegantOTA.h>

AsyncWebServer server(80); //For OTA updates


//VLX
#define LOX1_ADDRESS 0x30
#define LOX2_ADDRESS 0x31
#define SHT_LOX1 33
#define SHT_LOX2 32

Adafruit_VL53L0X lox1 = Adafruit_VL53L0X();
Adafruit_VL53L0X lox2 = Adafruit_VL53L0X();

int RANGE_DIFF1;
int RANGE_DIFF2;

#define LEDPCB    15
#define LEDBOARD  2

//direction PINS
//connect these 2 pins together to reverse the direction
//if connected, going in(Addition) means that VLX1 is triggered first (shut pin  32)
//if disconnected, going in means that VLX2 is triggered first (shut pin 33)
#define GPIO_INPUT    13
#define GPIO_OUTPUT   12

#define DELAYVAL   500 //prevent false triggering 15cm
const int ping_time = 10 * 60 * 1000; //10mins 
int ping_now = millis();


//debugging parameters, allows us to remove wifi and the serial printouts during production
const bool debugging = true;  
const bool wifi_off = false;
int counter = 0; //debugging

// Dining Wifi
const char * WifiSSID = "orcatech_dining_bot";
const char * WifiPassword = "ORCATECH_DINING_BOT_PASSWORD";
EspMQTTClient * WifiClient;
String WifiMAC;

// MQTT parameters
const char * MQTTServerIP = "192.168.4.1"; // RPi configured to this static IP
bool MQTTConnected = false;

uint16_t lo_cal[2] = {0,0};
 
//direction
bool lox1_in;

bool in_act = false; 
bool out_act = false;
int start_time;
bool wifi_connected = true;
int disconnect_time;

void setID() {
  /*
    Reset all sensors by setting all of their XSHUT pins low for delay(10), then set all XSHUT high to bring out of reset
    Keep sensor #1 awake by keeping XSHUT pin high
    Put all other sensors into shutdown by pulling XSHUT pins low
    Initialize sensor #1 with lox.begin(new_i2c_address) Pick any number but 0x29 and it must be under 0x7F. Going with 0x30 to 0x3F is probably OK.
    Keep sensor #1 awake, and now bring sensor #2 out of reset by setting its XSHUT pin high.
    Initialize sensor #2 with lox.begin(new_i2c_address) Pick any number but 0x29 and whatever you set the first sensor to
 */

  // all reset
  digitalWrite(SHT_LOX1, LOW);    
  digitalWrite(SHT_LOX2, LOW);
  delay(10);
  // all unreset
  digitalWrite(SHT_LOX1, HIGH);
  digitalWrite(SHT_LOX2, HIGH);
  delay(10);

  // activating LOX1 and resetting LOX2
  digitalWrite(SHT_LOX1, HIGH);
  digitalWrite(SHT_LOX2, LOW);

  // initing LOX1
  if(!lox1.begin(LOX1_ADDRESS)) {
    if(debugging) Serial.println(F("Failed to boot first VL53L0X"));
    while(1);
  }
  delay(10);

  // activating LOX2
  digitalWrite(SHT_LOX2, HIGH);
  delay(10);

  //initing LOX2
  if(!lox2.begin(LOX2_ADDRESS)) {
    if(debugging) Serial.println(F("Failed to boot second VL53L0X"));
    while(1);
  }
}

void VLXsetup(){
  //Initalise Pins, Set i2c IDs, and configure lox
  pinMode(SHT_LOX1, OUTPUT);
  pinMode(SHT_LOX2, OUTPUT);

  if(debugging) Serial.println(F("Shutdown pins inited..."));

  digitalWrite(SHT_LOX1, LOW);
  digitalWrite(SHT_LOX2, LOW);

  if(debugging) Serial.println(F("Both in reset mode...(pins are low)"));
  if(debugging) Serial.println(F("Starting..."));

  setID(); //Assign I2C address to the VLXes


  //set to long range, we found high speed was unable to detect movement for certain doors
  lox1.configSensor(Adafruit_VL53L0X::VL53L0X_SENSE_LONG_RANGE);
  lox2.configSensor(Adafruit_VL53L0X::VL53L0X_SENSE_LONG_RANGE);

  lox1.setDeviceMode(VL53L0X_DEVICEMODE_CONTINUOUS_RANGING);
  lox2.setDeviceMode(VL53L0X_DEVICEMODE_CONTINUOUS_RANGING);
  
  lox1.startRangeContinuous();
  lox2.startRangeContinuous();
}

void Blink(int LED){
  digitalWrite(LED,HIGH);
  delay(100);
  digitalWrite(LED,LOW);
  delay(100);
}

bool DirectionInOut(){
  //use this to decide which direction.
  //connect GPIO 13 to 26 to set direction as positive
  //not connected > default hit lox1 going in
  //connected > hit lox1 means going out

  pinMode(GPIO_INPUT,INPUT);
  pinMode(GPIO_OUTPUT,OUTPUT);

  delay(100);

  digitalWrite(GPIO_OUTPUT,HIGH);

  delay(100);
  if(digitalRead(GPIO_INPUT) == HIGH){
    digitalWrite(GPIO_OUTPUT,LOW);
    return false;
  }

  digitalWrite(GPIO_OUTPUT,LOW);
  return true;

}

void LoCalibrate(){
  //Calibration - if the wall is near, then a lower distance is needed to trigger the VLX

  uint16_t range1, range2, t1,t2;
  //Set t1, t2 as the maximum
   
  t1 = 10000;
  t2 = 10000;

  for(int i = 0;i<50; i++){
    while(!lox1.isRangeComplete() && !lox2.isRangeComplete()){}
    range1 = lox1.readRangeResult();
    range2 = lox2.readRangeResult();

    if(range1 > 10000) range1 = 2000;
    if(range2 > 10000) range2 = 2000;
    
    //We use minimum rather than the average
    t1 = min(t1,range1);
    t2 = min(t1,range2);
    
    delay(10);
  }

  lo_cal[0] = t1;
  lo_cal[1] = t2;

  
  digitalWrite(LEDBOARD,LOW);

  RANGE_DIFF1 = 0.25 * t1;
  RANGE_DIFF2 = 0.25 * t2;


  if(debugging) Serial.println("Calibration");
  if(debugging) Serial.println(lo_cal[0]);
  if(debugging) Serial.println(lo_cal[1]);


}

void setupOTA(){
  if(wifi_off) return;
  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send(200, "text/plain", ("Hi! I am ESP32." + WiFi.macAddress() ));
  });

  AsyncElegantOTA.begin(&server);    // Start ElegantOTA
  server.begin();
  Serial.println("HTTP server started");  
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21,22,1000000LU);

  pinMode(LEDPCB,   OUTPUT);
  pinMode(LEDBOARD, OUTPUT);

  digitalWrite(LEDBOARD,LOW); 

  VLXsetup();
  LoCalibrate();  //Calibrate when no one is at the sensors
  lox1_in = DirectionInOut(); //Set the direction based on the jumper wires

  if(!lox1_in){
    digitalWrite(LEDPCB,HIGH); // set led to be on when the non-default it set
    if(debugging) Serial.println("LOX1 > LOX2 = IN");
  }
  else{
    digitalWrite(LEDPCB,LOW);
    if(debugging) Serial.println("LOX2 > LOX1 = IN");
  }
 
  DiningWifi_Setup();
  setupOTA(); //Comes after due to wifi
  delay(1000);

  digitalWrite(LEDBOARD,HIGH); //Turn on LED once set up has finished
}


void loop() {
  DiningWifi_Loop(); //MQTT

  uint16_t range1 = lox1.readRangeResult();
  uint16_t range2 = lox2.readRangeResult();

  uint16_t range1_thresh = lo_cal[0]-RANGE_DIFF1; //to activate
  uint16_t range2_thresh = lo_cal[1]-RANGE_DIFF2;

  if(range1 == 0 || range1 >2000){
    range1 = 2000; // constrain to max length
  }
  
  if(range2 == 0|| range2>2000){
    range2 = 2000; // constrain to max length
  }


  if( !in_act && !out_act){
    if( (range1 < range1_thresh) && (range2 < range2_thresh) ){
      delay(1); //Both are actiavted, just continue
     }
    else if(range1<range1_thresh){
      in_act = true;
      start_time = millis();
    }
    else if(range2<range2_thresh){
      out_act = true;
      start_time = millis();
    }
  }
    

  if(millis() - start_time > 500 ){
    in_act = false;
    out_act = false;
  }

  else if(in_act){
    if(range2 < range2_thresh){
      in_act = false;
      if(debugging){
        Serial.print(range1);
        Serial.print(" ");
        Serial.println(range2);
      }

      if(lox1_in){
        counter++;
        DiningWifi_HandleIncrement();
//        if(debugging) Serial.println(counter);
//        if(debugging) Serial.println("Increase");
      }
      else{
        counter--;
        DiningWifi_HandleDecrement();
//        if(debugging) Serial.println(counter);
//        if(debugging) Serial.println("Decrease");
      }

      delay(DELAYVAL);
    }
  

  }

  else if(out_act){
    if(range1 < range1_thresh){
      out_act = false;
      if(debugging){
        Serial.print(range1);
        Serial.print(" ");
        Serial.println(range2);
      }
      
      if(lox1_in){
        counter--;
        DiningWifi_HandleDecrement();
//        if(debugging) Serial.println(counter);
//        if(debugging) Serial.println("Decrease");
      }
      else{
        counter++;
        DiningWifi_HandleIncrement();
//        if(debugging) Serial.println(counter);
//        if(debugging) Serial.println("Increase");
      }

      delay(DELAYVAL);
    }
      
  }

  if(!wifi_off && WiFi.status() != WL_CONNECTED){
    //If wifi is not connected, change flag, start time, attempt reconnection
    if(wifi_connected == true){
      disconnect_time = millis();
      wifi_connected = false;
    }

    WiFi.disconnect();
    WiFi.reconnect();
    
  }
  else if(!wifi_off && wifi_connected == false && WiFi.status() == WL_CONNECTED){
    //If there is connection, AND it was previously not connected, reset flag, send time taken to connect back
    wifi_connected = true;
    Wifi_ReconnectTime(millis() - disconnect_time);

  }
  
  //PING
  if(millis() - ping_now >= ping_time){
    Wifi_PingConnection();
    ping_now = millis(); //RESET time
  }
  
  
  //Debugging purposes
  if(debugging) Serial.print(range1);
  if(debugging) Serial.print(" ");
  if(debugging) Serial.print(range2);
  if(debugging) Serial.print(" ");
  if(debugging) Serial.println(counter);
  


}

void DiningWifi_Setup() {
  // Get device MAC address
  if(wifi_off) return;
  if(debugging) Serial.print("ESP Board MAC Address:  ");
  WifiMAC = WiFi.macAddress();
  if(debugging) Serial.println(WifiMAC);

  // Start Wifi with MQTT
  WifiClient  = new EspMQTTClient(
    WifiSSID, // WifiSSID
    WifiPassword, // WifiPassword
    MQTTServerIP,  // MQTT Broker server ip
    NULL,   // MQTTUsername, Can be omitted if not needed
    NULL,   // MQTTPassword, Can be omitted if not needed
    WifiMAC.c_str(),     // Client name that uniquely identify your device
    1883              // The MQTT port, default to 1883. this line can be omitted
  );

  // Optional functionalities of EspMQTTClient
  WifiClient->enableDebuggingMessages(); // Enable debugging messages sent to serial output
  //WifiClient.enableHTTPWebUpdater(); // Enable the web updater. User and password default to values of MQTTUsername and MQTTPassword. These can be overridded with enableHTTPWebUpdater("user", "password").
  //WifiClient.enableOTA(); // Enable OTA (Over The Air) updates. Password defaults to MQTTPassword. Port is the default OTA port. Can be overridden with enableOTA("password", port).
  //WifiClient->enableLastWillMessage("TestClient/lastwill", "I am going offline");  // You can activate the retain flag by setting the third parameter to true

  // Wait until connected to Wifi
  do {
    WifiClient->loop();
  } while(WiFi.status() != WL_CONNECTED);
  if(debugging) Serial.println("Connected to Wifi");
}

void DiningWifi_Loop() {
  if(wifi_off) return;
  // MQTT library handle
  WifiClient->loop();
}

void Wifi_PingConnection(){
  if(wifi_off || (WiFi.status() != WL_CONNECTED)) return;
  
  WifiClient->publish("dh_topic/connection/"+WifiMAC, "ESP32 connected -> ");
  
}

void Wifi_ReconnectTime(int time_taken){
  if(wifi_off || (WiFi.status() != WL_CONNECTED)) return;
  WifiClient->publish("dh_topic/reconnect/"+WifiMAC+"/"+String(time_taken), "ESP32 connected back");

}

void DiningWifi_HandleIncrement() {
  if(wifi_off) return;
  bool res = WifiClient->publish("dh_topic/increment/"+WifiMAC, "ESP32 connected");
  if(!res) digitalWrite(LEDBOARD,LOW);
  else digitalWrite(LEDBOARD,HIGH);
  return;
}

void DiningWifi_HandleDecrement() {
  if(wifi_off) return;
  bool res = WifiClient->publish("dh_topic/decrement/"+WifiMAC, "ESP32 connected");
  if(!res) digitalWrite(LEDBOARD,LOW);
  else digitalWrite(LEDBOARD,HIGH);
  return;
}

// This function is called once everything is connected (Wifi and MQTT)
// WARNING : YOU MUST IMPLEMENT IT IF YOU USE EspMQTTClient
void onConnectionEstablished() {
  // Publish a test message once we have connected
  if(wifi_off) return;
  WifiClient->publish("dh_topic/test/"+WifiMAC+"/"+WiFi.localIP().toString().c_str(), "ESP32 connected -> ");

  MQTTConnected = true;
}
