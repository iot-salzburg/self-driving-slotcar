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

//the last time i sent the message
int begin_time;

char* data; //the data to be sent as a string in json format

//a buffer which will be sent also. mainly in case the connection fails for a second.
char* data_buffer;
int size_data_buffer;


int data_index; //where the data should be stored in the buffer. 
void setup() {
  data = (char*)calloc(250, sizeof(char));
  data_buffer = (char*)calloc(500, sizeof(char));
  size_data_buffer = 500;
  data_index = 0;
  
  //serial will not work with i2c given the way i am implementing it
  //Serial.begin(9600);
  begin_time = millis();

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
  while (!client.connected()) {
    //attempt to connect
      read_format_data(); //in case connection breaks it will still add to the buffer. 
    if (client.connect("ESP8266 client")) {
      
    } else {
      delay(5000); //should implement a mechanism so it stores the data offline in a buffer and then sends the data. 
    }
  }
}


void loop() {

  read_format_data();
    if (!client.connected()) {
    reconnect_mqtt();
   client.loop(); //This should be called regularly to allow the client to process incoming messages and maintain its connection to the server.
  } else {
      sprintf((data_buffer+data_index-1), "]");
      client.loop(); //This should be called regularly to allow the client to process incoming messages and maintain its connection to the server.
      client.publish(topic, data_buffer);
      data_index = 0;

  }


}
// reading the data into a predifined and allocated array. makes more sense from an efficiency perspective. If needed, this data can still be used and put in an array.
//AKS WETHER IT IS OK TO JUST MODIFY GLOBAL VARIABLES AND NOT TO RETURN ANYTHING.
void read_format_data() {
  // get mpu data
  Wire.beginTransmission(i2c_addr);
  Wire.write(0x3B); //starting with register 0x3B(ACCEL_XOUT_H). Any read will happen from here on. https://www.invensense.com/wp-content/uploads/2015/02/MPU-6000-Register-Map1.pdf check the map to see which registers might be needed
  Wire.endTransmission(false);
  Wire.requestFrom(i2c_addr, 14, true);
  int32_t AcX = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read()); //look at data sheet. Adding the first and last byte accordingly. looking after two's complement
  int32_t AcY = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t AcZ = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t Temperature = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t gyroX = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t gyroY = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int32_t gyroZ = (int32_t)(int16_t)(Wire.read() << 8 | Wire.read());
  int now_time = millis();
  if(data_index == 0){
    sprintf(data_buffer, "[");
    data_index++;
  }
  if(data_index == size_data_buffer-150){
    data_buffer = (char*)realloc(data_buffer, size_data_buffer*2); //should make this safer. in case it fails. ANY IDEAS TO WHOEVER READS THIS? it's about when realloc returns null (same issue for calloc).\
    size_data_buffer *= 2;
  }
  data_index += sprintf((data_buffer+data_index), "{\"AcX\": %d, \"AcY\": %d, \"AcZ\": %d, \"GyroX\": %d, \"GyroY\": %d, \"GyroZ\": %d, \"Time\": %d},", (int)AcX, AcY, AcZ, gyroX, gyroY, gyroZ, (now_time - begin_time));
}

int determine_i2c_addr() {
  //to determine which i2c address the accelerometer has
  for (int addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (!Wire.endTransmission()) {
      char msg[5];
      sprintf(msg, "%d", addr);
      client.publish(topic, msg);
    }
  }
}

int* copy_arr(int* src, int* dst, int arr_length) {
  for (int i = 0; i < arr_length; i++) {
    dst[i] = src[i];
  }
  return dst;
}
