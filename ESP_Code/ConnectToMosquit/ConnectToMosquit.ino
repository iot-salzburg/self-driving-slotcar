//loosly following mqtt set up as specified by: www.baldengineer.com/mqtt-tutorial.html
//also following www.playground.arduino.cc/Main/MPU-6050 to read accelerometer data

#include <Wire.h>
#include <PubSubClient.h>
#include <ESP8266WiFi.h>

//wifi/mqtt settings
const char* ssid = "sensornet";
const char* password = "senSO!netIot";
const char* mqtt_server = "192.168.48.188";
const char* topic = "Test_topic";

//Set clients
WiFiClient espClient;
PubSubClient client(espClient);

//the i2c address found
const int i2c_addr = 104;

//the counter to know how many data points to send for calibration
int cal_counter = 0;
//the number of data points to send for calibration
int num_cal = 20;

//the last time i sent the message
int* last_time;

void setup() {
  //serial will not work with i2c given the way i am implementing it
  //Serial.begin(9600); 
  cal_counter = 0;
  last_time = (int *)malloc(3 * sizeof(int));
  
  //connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
  
  //need to initialize the pins to be used for i2c. Refer to www.instructables.conm/id/How-to-use-the-ESP8266-01-pins/
  Wire.begin(1, 3);

  //setting up the MPU6050. Refer to Wire documentation
  Wire.beginTransmission(i2c_addr);
  Wire.write(0x6B); //PWR_MGMG_1 register to wake up
  Wire.write(0); //set to zero (wakes up the MPU-6050)
  Wire.endTransmission(true);

  //port 1883 is reserved for mqtt services
  client.setServer(mqtt_server, 1883);
}

//connect with mqtt server as ESP8266 client
void reconnect_mqtt() {
  //loop until conntected
  while (!client.connected()) {
    //attempt to connect
    if (client.connect("ESP8266 client")){  
      
    } else {
      delay(5000); //wait to reconnect
    }
  }
}


void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();
  //to determine which i2c address the accelerometer has
  //  for(int addr = 1; addr < 127; addr++){
  //    Wire.beginTransmission(addr);
  //    if(!Wire.endTransmission()){
  //      char msg[5];
  //      sprintf(msg, "%d", addr);
  //      client.publish(topic, msg);
  //    }
  //  }

  // get mpu data
  Wire.beginTransmission(i2c_addr);
  Wire.write(0x3B); //starting with register 0x3B(ACCEL_XOUT_H)
  Wire.endTransmission(false);
  Wire.requestFrom(i2c_addr, 6, true);
  int32_t AcX = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read()); //look at data sheet. Adding the first and last byte accordingly. looking after two's complement
  int32_t AcY = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t AcZ = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  
  int acc_data[] = {AcX, AcY, AcZ};
  //start calibration process
  if (cal_counter == 0) {
    client.publish(topic, "0/Place the object flat on a surface. Calibration will start in 5 seconds."); //0 indicates the warning that calibration will start
    char msg_num_cal[50];
    sprintf(msg_num_cal, "1/%d", num_cal);
    client.publish(topic, msg_num_cal); //1 indicates how many calibration cycles we will have
    delay(5000);
    client.publish(topic, "2/start calibration"); //2 indicates the start of calibration
  } else if (cal_counter == num_cal) {
    client.publish(topic, "3/end calibration"); //3 indicates end of calibration
    client.publish(topic, "4/start data transfer"); //4 indicates start of normal data transfer
  }
  int now_time[3];
  char acc = 'X';
  //much better to send as one packet!!!!!!! MUST BE CHANGED. code on raspberry will work with only the time as given by the X acceleration. 
  for (int i = 0; i < 3; i++) {
    char msg[100];
    now_time[i] = millis();
    int use_time = last_time[i] == 0 && cal_counter >= num_cal ? 0 : now_time[i] - last_time[i];
    sprintf(msg, "5/%c acceleration: %d.|%d", acc + i, acc_data[i], use_time);
    client.publish(topic, msg); //5 inicates normal data transfer message
  }
  cal_counter++;
  if(cal_counter < 20){
      delay(500);
  }

  last_time = copy_arr(now_time, last_time, 3);

}

  int* copy_arr(int* src, int* dst, int arr_length){
    for(int i = 0; i < arr_length; i++){
      dst[i] = src[i];
    }
    return dst;
  }
