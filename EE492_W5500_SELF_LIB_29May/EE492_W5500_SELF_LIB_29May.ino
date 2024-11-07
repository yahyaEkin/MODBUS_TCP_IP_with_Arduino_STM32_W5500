#include <w5500.h>
#include <socket.h>
#include <wizchip_conf.h>

#define NUM_OF_REGS 125 //SAME NUMBER IS USED FOR INPUT REGISTERS.
#define NUM_OF_COILS 8
#define NUM_OF_DISCRETE_INPUTS 8
/*  WHILE DEFINING THE NUMBER OF REGISTERS, COILS, INPUT REGISTERS, WE NEED
 *  TO CONSIDER THE REMOTE DEVICE SPECIFICAT  ONS. FOR INSTANCE, THIS DEVICE HAS 2
 *  RELAY OUTPUTS (COILS) AND THREE DISCRETE INPUT PINS (ANALOG INPUT PINS).
 *  BUT FOR THE TEST CASES OF MASTER PROGRAM, WE DEFINE HIGHER NUMBER OF INPUT REGISTERS
 *  AND COILS THAN WE HAVE IN THIS DEVICE.
 */
#define MBAP_SIZE 7
//MACRO FOR CALCULATING ARRAY SIZE
#define elemansayisi_array(arr)   (sizeof(arr)/sizeof(arr[0])) 
//Röle Pinler
#define DiscreteInput1 7
#define DiscreteInput2 8
#define AnalogInput1 A0
#define AnalogInput2 A1
#define Coil1 2
#define Coil2 4

int AnalogInput1_Val;
int AnalogInput2_Val;
int DiscreteInput1_Val;
int DiscreteInput2_Val;

unsigned short HOLDING_REGISTERS[NUM_OF_REGS];
unsigned short INPUT_REGISTERS[NUM_OF_REGS];
unsigned short COILS[NUM_OF_COILS];
unsigned short DISCRETE_INPUTS[NUM_OF_DISCRETE_INPUTS];
// MAC adresi (denetim masasındaki fiziksel adres)
uint8_t mac[6] = {0xB0, 0x34, 0xCB, 0x3E, 0x31, 0xDB};

// IP adresi (benzersiz bir adres)
uint8_t ip[4] = {192, 168, 0, 10};

// Ağ maskesi ve varsayılan ağ geçidi
uint8_t sn[4] = {255, 255, 255, 0};
uint8_t gw[4] = {192, 168, 0, 1};


//Receive message
// SPI kontrol fonksiyonları
void csSelect() {
  PORTB &= ~_BV(PORTB2);  // CS pin LOW
}

void csDeselect() {
  PORTB |= _BV(PORTB2);   // CS pin HIGH
}

uint8_t spiTransfer(uint8_t data) {
  SPDR = data;                     // Veri gönder
  while (!(SPSR & _BV(SPIF))) ;    // Transfer bitene kadar bekle
  return SPDR;                     // Alınan veriyi döndür
}

unsigned int arrayToDecimal(int a[], int length) {
    unsigned int decimal_val = 0;
    for (int i = 0; i < length; i++) {
        decimal_val = (decimal_val << 1) | a[i];
    }
    return decimal_val;
}

///Decimal bir değeri Hex sayısına çevirmek için (arrayToHex den gelen sayıyı hex formatına çevirir)
char* decimalToHex(unsigned int decimal) {
    char* hexValue = (char*)malloc(sizeof(char) * 10); // Bellekte alan ayır, maksimum 10 karakterlik hex değeri
    if(hexValue == NULL) {
        printf("Bellek tahsisi basarisiz!\n");
        exit(1);
    }
    sprintf(hexValue, "%X", decimal); // Ondalık sayıyı hexadecimal olarak dönüştür
    return hexValue;
}

//Hexadecimal to decimal converts
uint8_t hexToDecimal(uint8_t hex) {
    uint8_t decimal = 0;

    if (hex >= '0' && hex <= '9') {
        decimal = hex - '0';
    } else if (hex >= 'A' && hex <= 'F') {
        decimal = hex - 'A' + 10;
    } else if (hex >= 'a' && hex <= 'f') {
        decimal = hex - 'a' + 10;
    }

    return decimal;
}

//Decimal to High-Low Byte Hexidecimal value
uint8_t *Dec2Hex(uint16_t c){
    uint8_t high_byte = (c>>8) & 0xFF;
    uint8_t low_byte = c & 0xFF;

    uint8_t *result = malloc(2*sizeof(uint8_t));
    result[0] = high_byte;
    result[1] = low_byte;

    return result;
}

/*Modbus TCP/IP functions from 1 to 6*/
//01 (0x01) Read Coils 
uint8_t *READ_COILS(uint8_t function_code,uint8_t start_address, uint8_t quantity_of_coils){
  //RES PDU'nun uzunluğu quantity of inputsun değerine göre değişiyor.
  int length_res_pdu;
  int byte_count;
  if(quantity_of_coils>8){
    //Burada response uzunluğunun belirlenmesi için quantity of inputs sayısının 8 e bölünmesi gerekir.
    //Tam kısmı bizim byte sayımızı oluşturur. Eğer 8 e tam bölünmüyorsa artık bitler için ekstra bir byte
    //atanması gerekir.
    byte_count = quantity_of_coils /8;
    if(quantity_of_coils %8 != 0){
      byte_count++;
    }
  }else{
    byte_count=1;
  }
  //response length = 1 byte(function code) + 1 byte(byte count) + output status byte
  length_res_pdu = byte_count +2;

  uint8_t *RES_PDU_1 = malloc(length_res_pdu*sizeof(uint8_t));

  RES_PDU_1[0] = function_code; //Function code
  RES_PDU_1[1] = byte_count; //byte count
  
  for(int i = 0; i<NUM_OF_COILS; i++)
      {
        Serial.print("Coil");
        Serial.print(i);
        Serial.print(": ");
        Serial.println(COILS[i]);
      }
  // Coilleri 8-bitlik gruplar halinde al ve hexadecimal forma dönüştür
	for (int i = 0; i < byte_count; i++) {
		uint8_t byte_value = 0;
		for (int j = 0; j < 8; j++) {
			byte_value |= (COILS[start_address + i * 8 + j] << j);
		}
		RES_PDU_1[i + 2] = byte_value;
	}
  return RES_PDU_1;
}

//02 (0x02) Read Discrete Input
uint8_t *READ_DISCRETE_INPUTS(uint8_t function_code, uint8_t start_address, uint8_t quantity_of_inputs){
  //RES PDU'nun uzunluğu quantity of inputsun değerine göre değişiyor.
  int length_res_pdu;
  int byte_count;

  if(quantity_of_inputs>8){
    //Burada response uzunluğunun belirlenmesi için quantity of inputs sayısının 8 e bölünmesi gerekir.
    //Tam kısmı bizim byte sayımızı oluşturur. Eğer 8 e tam bölünmüyorsa artık bitler için ekstra bir byte
    //atanması gerekir.
    byte_count = quantity_of_inputs /8;
    if(quantity_of_inputs %8 != 0){
      byte_count++;
    }
  }else{
    byte_count=1;
  }
  //response length = 1 byte(function code) + 1 byte(byte count) + output status byte
  length_res_pdu = byte_count +2;

  uint8_t *RES_PDU_2 = malloc(length_res_pdu*sizeof(uint8_t));

  RES_PDU_2[0] = function_code;
  RES_PDU_2[1] = byte_count;

  int discrete1_status = digitalRead(DiscreteInput1);
  int discrete2_status = digitalRead(DiscreteInput2);
  int status_role[8] = {discrete2_status,discrete1_status,0,0,0,0,0,0};
    
    for (int i = 0; i < byte_count; i++) {
		uint8_t byte_value = 0;
		for (int j = 0; j < 8; j++) {
			byte_value |= (status_role[start_address + i * 8 + j] << j);
		}
		RES_PDU_2[i + 2] = byte_value;
	}
/*  int result_array_to_decimal = arrayToDecimal(status_role,elemansayisi_array(status_role));
  Serial.print("Array to dec: ");
  Serial.println(result_array_to_decimal);
  char *hexString = decimalToHex(result_array_to_decimal);
  int con_hexString = atoi(hexString); //char olarak uint8 tipinde bir arraye atamayız. O yüzden char stringi int tipine dönüştürdüm.
  Serial.print("Hex format: ");
  Serial.println(con_hexString);
  //Sadece iki adet röle girişi olduğundan sadece üç elemanlı bir RESPONSE PDU arrayi oluşturulmuştur.

  RES_PDU_2[2] = (uint8_t)con_hexString;
*/ 
  Serial.println(RES_PDU_2[2]);
  return RES_PDU_2;
}



//03 (0x03) Read Holding Registers 
uint8_t *READ_H_REGS( uint8_t function_code, uint8_t start_address, uint8_t quantity_of_inputs)
{
  // RES_PDU nun uzunluğu 2*quantity_of_inputs (1byte*2) + byte_count(1 byte) + function_code(1byte)
  int length_res_pdu = 2*quantity_of_inputs + 1 + 1;
  
  //Adjustment to memory dynamically
  uint8_t *RES_PDU_3 = malloc(length_res_pdu*sizeof(uint8_t));

  uint8_t byte_count = 2*quantity_of_inputs;
  RES_PDU_3[0] = function_code;
  RES_PDU_3[1] = byte_count;

  //Burada Arduino'nun Analog Output çıkışlarını okuyacak değerler yer alacak
  for(int i = 0; i<quantity_of_inputs; i++)
  {
    RES_PDU_3[(2*i)+2] = highByte(HOLDING_REGISTERS[start_address + i]);
    RES_PDU_3[(2*i)+3] = lowByte(HOLDING_REGISTERS[start_address + i]);
  }
  Serial.print("RES_PDU ");
  for (int i = 0; i < length_res_pdu; i++) 
  {
    Serial.print("/x");
    Serial.print(RES_PDU_3[i], HEX);
    Serial.print(" ");
  }
  return RES_PDU_3;
}

//04 (0x04) Read Input Registers (analogRead() fonksiyonuyla analog voltaj girişlerini okuyabiliyoruz)
uint8_t *READ_IN_REGS(uint8_t function_code, uint8_t start_address, uint8_t quantity_of_inputs){
  // RES_PDU nun uzunluğu 2*quantity_of_inputs (1byte*2) + byte_count(1 byte) + function_code(1byte)
  int length_res_pdu = 2*quantity_of_inputs + 1 + 1;

  //Adjustment to memory dynamically
  uint8_t *RES_PDU_4 = malloc(length_res_pdu*sizeof(uint8_t));

  uint8_t byte_count = 2*quantity_of_inputs;
  RES_PDU_4[0] = function_code;
  RES_PDU_4[1] = byte_count;


  //Burada Arduino'nun Analog Input giriş değerlerini okuyan (kaç tane ise) değerler yer alacak. 
  //Eğer birden fazla ise switch case yapısı ile for döngüsü yapılmalı yada if-else if condition şeklinde 
  for(int i = 0; i<quantity_of_inputs; i++)
  {
    RES_PDU_4[(2*i)+2] = highByte(INPUT_REGISTERS[start_address + i]);
    RES_PDU_4[(2*i)+3] = lowByte(INPUT_REGISTERS[start_address + i]);
  }
  Serial.print("RES_PDU ");
  for (int i = 0; i < length_res_pdu; i++) 
  {
    Serial.print("/x");
    Serial.print(RES_PDU_4[i], HEX);
    Serial.print(" ");
  }
  return RES_PDU_4;
}
// 06 (0x06) Write Single Register
uint8_t *WRITE_SINGLE_REGISTER(uint8_t function_code,uint8_t register_address,uint16_t register_value){
  /*
            THIS FUNCTION IS USED TO WRITE SINGLE HOLDING REGISTER IN REMOTE DEVICE
            REQUEST IS THE ECHO OF THE RESPONSE
            
            REQUEST     FUNCTION CODE       1BYTE   0X06
                        REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                        REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF
            RESPONSE    FUNCTION CODE       1BYTE   0X06
                        REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                        REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF   
  */
  // RESPONSE PDU LENGTH = 5 BYTE 
  HOLDING_REGISTERS[register_address] = register_value;

  int length_res_pdu = 5;
  uint8_t *output_address_high_low_byte = Dec2Hex(register_address);
  uint8_t *output_value_high_low_byte = Dec2Hex(register_value);
  
  uint8_t *RES_PDU_6 = malloc(length_res_pdu*sizeof(uint8_t));
  
  RES_PDU_6[0] = function_code;
  for(int i=0;i<2;i++){
      RES_PDU_6[i+1] = *(output_address_high_low_byte + i);
    }
  for(int i=0;i<2;i++){
      RES_PDU_6[i+3] = *(output_value_high_low_byte+i);
    }
  Serial.print("RES_PDU_6");
    for(int i=0;i<length_res_pdu;i++){
        Serial.print("/x");
        Serial.print(RES_PDU_6[i], HEX);
        Serial.print(" ");     
    }
    
    return RES_PDU_6;
}



//05 (0x5) Write Single Coil 
uint8_t *WRITE_SINGLE_COIL(uint8_t function_code,uint8_t output_address,uint16_t output_value){
    //RES PDU nun uzunluğu 5 byte = 1 byte (Function code) + 2byte (Output Address) + 2 byte (Output value)
    int length_res_pdu = 5;
    uint8_t *output_address_high_low_byte = Dec2Hex(output_address);
    uint8_t *output_value_high_low_byte = Dec2Hex(output_value);
    //Adjustment to memory dynamically
    uint8_t *RES_PDU_5 = malloc(length_res_pdu*sizeof(uint8_t));

    RES_PDU_5[0] = function_code;
    
    if (output_value == 65280)
    {
       COILS[output_address] = 1;
       Serial.print("Stat:COIL");
       Serial.print(output_address);
       Serial.print(": ");
       Serial.println(1);
    }
    else
     COILS[output_address] = 0;
       Serial.print("Stat:COIL");
       Serial.print(output_address);
       Serial.print(": ");
       Serial.println(1);

    //Burada bir dijital bir pin çıktısı adresi atanması lazım.
    for(int i=0;i<2;i++){
      RES_PDU_5[i+1] = *(output_address_high_low_byte + i);
    }
    //Eğer output value 0xFF00 (aslında 0xFF ama high byte FF low byte 00 olarak ayarlanmış) ise 
    //digitalWrite(output_adress,HIGH) olarak dijital pin aktif edilmelidir. Bu fonksiyona yazılmalıdır
    for(int i=0;i<2;i++){
      RES_PDU_5[i+3] = *(output_value_high_low_byte+i);
    }

    Serial.print("RES_PDU ");
    for(int i=0;i<length_res_pdu;i++){
        Serial.print("/x");
        Serial.print(RES_PDU_5[i], HEX);
        Serial.print(" ");     
    }
    
    return RES_PDU_5;
}

uint8_t *COMBINE_MBAP_PDU(uint8_t *MBAP, uint8_t *PDU,int size_MBAP,int size_PDU)
{
  int size_all = size_MBAP + size_PDU;
  uint8_t *COMPLETE_FRAME = malloc(size_all * sizeof(uint8_t));

  
  for(int i = 0; i<size_MBAP; i++)
  {
    COMPLETE_FRAME[i] = MBAP[i];
  }
  for (int i = 0; i<size_PDU; i++)
  {
    COMPLETE_FRAME[i + size_MBAP] = PDU[i];
  }
  Serial.println("COMPLETE_FRAME: ");
  for (int i = 0; i < size_all; i++) 
  {
    Serial.print("/x");
    Serial.print(*(COMPLETE_FRAME+i), HEX);
    Serial.print(" ");
  }
  Serial.println(" ");
  return COMPLETE_FRAME;
}


void setup() {
  Serial.begin(9600);

  // SPI başlatma
  pinMode(10, OUTPUT);      // CS pin
  pinMode(11, OUTPUT);      // MOSI
  pinMode(12, INPUT);       // MISO
  pinMode(13, OUTPUT);      // SCK
  csDeselect();
  
  SPCR |= _BV(MSTR);        // Master mod
  SPCR |= _BV(SPE);         // SPI etkin

  // W5500'ü başlatma ve yapılandırma
  wizchip_init(0, 0);  // Buffer boyutlarını belirtmeden başlatma
  reg_wizchip_cs_cbfunc(csSelect, csDeselect);
  reg_wizchip_spi_cbfunc(spiTransfer, spiTransfer);

  // Ağ bilgilerini yapılandırma
  wiz_NetInfo netInfo = {
    .mac = {mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]},
    .ip = {ip[0], ip[1], ip[2], ip[3]},
    .sn = {sn[0], sn[1], sn[2], sn[3]},
    .gw = {gw[0], gw[1], gw[2], gw[3]}
  };

  wizchip_setnetinfo(&netInfo);

  // Ayarlanan ağ bilgilerini kontrol edin
  wizchip_getnetinfo(&netInfo);

  pinMode(DiscreteInput1, INPUT);
  pinMode(DiscreteInput2, INPUT);
  pinMode(AnalogInput1, INPUT);
  pinMode(AnalogInput2, INPUT);
  pinMode(Coil1, OUTPUT);
  pinMode(Coil2, OUTPUT);

  HOLDING_REGISTERS[100] = 355; //buraya A/D I/O pinleri gelecek. Pinler belirlendikten sonra denemeler yapılır. 
  HOLDING_REGISTERS[101] = 356; //buraya A/D I/O pinleri gelecek. Pinler belirlendikten sonra denemeler yapılır. 
  
  Serial.print("IP Address: ");
  Serial.print(netInfo.ip[0]);
  Serial.print(".");
  Serial.print(netInfo.ip[1]);
  Serial.print(".");
  Serial.print(netInfo.ip[2]);
  Serial.print(".");
  Serial.println(netInfo.ip[3]);

  Serial.print("Subnet Mask: ");
  Serial.print(netInfo.sn[0]);
  Serial.print(".");
  Serial.print(netInfo.sn[1]);
  Serial.print(".");
  Serial.print(netInfo.sn[2]);
  Serial.print(".");
  Serial.println(netInfo.sn[3]);

  Serial.print("Gateway: ");
  Serial.print(netInfo.gw[0]);
  Serial.print(".");
  Serial.print(netInfo.gw[1]);
  Serial.print(".");
  Serial.print(netInfo.gw[2]);
  Serial.print(".");
  Serial.println(netInfo.gw[3]);

  
  Serial.println("COILS INITILAZED:");
  for(int i = 0; i<NUM_OF_COILS; i++)
      {
        COILS[i] = 0;
        Serial.print("Coil");
        Serial.print(i);
        Serial.print(": ");
        Serial.println(COILS[i]);
      }
      Serial.println("DISCRETE_INPUTS INITILAZED:");
  for(int i = 0; i<NUM_OF_DISCRETE_INPUTS; i++)
      {
       DISCRETE_INPUTS[i] = 0;
        Serial.print("Discrete Input");
        Serial.print(i);
        Serial.print(": ");
        Serial.println(DISCRETE_INPUTS[i]);
      }
  for(int i = 0; i<NUM_OF_REGS; i++)
      {
       INPUT_REGISTERS[i] = 0;
      }
  // Test mesajı
  Serial.println("Setup completed");

  // Soket başlatma
  uint8_t socketNumber = 0;
  socket(socketNumber, Sn_MR_TCP, 502, 0);

  // Dinlemeye başla
  if (listen(socketNumber) == SOCK_OK) {
    Serial.println("Listening on port 502...");
  } else {
    Serial.println("Failed to start listening");
    while (1);
  }
}

void loop() 
{
      // put your main code here, to run repeatedly:
      INPUT_REGISTERS[0] = analogRead(AnalogInput1);
      INPUT_REGISTERS[1] = analogRead(AnalogInput2);
      DISCRETE_INPUTS[0] = digitalRead(DiscreteInput1);
      DISCRETE_INPUTS[1] = digitalRead(DiscreteInput2);
      
      if (COILS[0] == 1)
      {
        digitalWrite(Coil1,HIGH);
      }
      else
        digitalWrite(Coil1,LOW);
      if (COILS[1] == 1)
      {
        digitalWrite(Coil2,HIGH);
      }
      else
        digitalWrite(Coil2,LOW);

      if (DISCRETE_INPUTS[1]==1){
        for(int i = 0; i<NUM_OF_COILS; i++)
          {
            Serial.print("Coil");
            Serial.print(i);
            Serial.print(": ");
            Serial.println(COILS[i]);
          }}

      uint8_t socketNumber = 0;
      uint8_t receive_message[12]; 
      uint8_t status = getSn_SR(socketNumber);
      if (status == SOCK_ESTABLISHED) 
          {
            Serial.println("Client connected");

            // Bağlantı kabul edildiğinde mesaj gönder
            //send(socketNumber, (uint8_t *)message, sizeof(message)); //====> bu bizim göndereceğimiz mesaj formatı

            //Receive fonksiyonu bu şekilde 
            recv(socketNumber, (uint8_t *)receive_message, 12);
            for(int i=0;i<12;i++){
              Serial.print("/");
              Serial.print(receive_message[i],HEX);
              Serial.print(" ");
            }

            unsigned short transaction_id = (receive_message[0] << 8) | receive_message[1]; // First byte is the function code
            unsigned short protocol_id = (receive_message[2] << 8) | receive_message[3]; // Combine the next two bytes into a short
            unsigned short t_length = (receive_message[4] << 8) | receive_message[5]; // Combine the last two bytes into a short
            byte unit_id = receive_message[6];
            byte function_code = receive_message[7];

            Serial.print("transaction_id: ");
            Serial.println(transaction_id);
            Serial.print("protocol_id: ");
            Serial.println(protocol_id);
            Serial.print("t_length: ");
            Serial.println(t_length);
            Serial.print("unit_id: ");
            Serial.println(unit_id, HEX);
            Serial.print("Function Code: ");
            Serial.println(function_code, HEX);
            if (unit_id == 1)
            {
              Serial.println("Unit ID OK...");
              Serial.println("##### Starting Functions ####");

              byte MBAP[7];
              MBAP[0] = highByte(transaction_id);
              MBAP[1] = lowByte(transaction_id);
              MBAP[2] = highByte(protocol_id);
              MBAP[3] = lowByte(protocol_id);
              /*MBAP[4] = highByte(response_t_length_f3_f4); \
                                                              --------> Bu iki byte sadece Function3 ve Function4 için geçerli, 
                                                              --------> o yüzden bu iki byte ilgili fonksiyonlarda tanımlanmışlardır.
              MBAP[5] = lowByte(response_t_length_f3_f4);  */
              MBAP[6] = unit_id;
              /* FROM THIS POINT, WE ARE TRYING TO SOLVE THE REQUEST PDU ACCORDING TO RELATED FUNCTION CODE*/

              if (function_code == 1){
                unsigned short start_address = (receive_message[8] << 8)| receive_message[9];               //Coils de Output Address olarak alınacak.
                unsigned short quantity_of_coils = (receive_message[10] << 8)| receive_message[11];        //Coils de Output value olarak alınacak.
                Serial.print("Start Address: ");
                Serial.println(start_address);
                Serial.print("Quantity of Coils: ");
                Serial.println(quantity_of_coils);
                
                uint8_t response_pdu_length; // CALCULATION OF THE RESPONSE PDU LENGTH
                  uint8_t byte_count;
                  //MBAP mesaj uzunluğunu bulmak için quantity of inputs sayısına bakılmalıdır.
                  //Fonksiyondaki mantık burada da yapılmıştır.
                  if(quantity_of_coils >8)
                    {
                      byte_count = quantity_of_coils /8;
                      if(quantity_of_coils %8 != 0)
                        {
                          byte_count++;
                        }
                    }
                  else
                    {
                      byte_count = 1;
                    }
                  //uint_identifier (1byte ) + function code(1 byte) + byte count (1 byte)
                  response_pdu_length = byte_count + 3;
                  MBAP[4] = highByte(response_pdu_length);
                  MBAP[5] = lowByte(response_pdu_length);

                  //Size RES_PDU boyutunu tanımla 
                  int size_RES_PDU = byte_count + 2;
                  //Fonksiyonu çağır ve geçici olarak PDU temp pointera ata (dönen değerlerin başlangıç adresi)
                  uint8_t *RES_PDU_TEMP = READ_COILS(function_code,start_address,quantity_of_coils);
                  //PDU arrayini olustur
                  uint8_t RES_PDU_1[size_RES_PDU];
                  //Temp pointerindaki değerleri PDU_1 e al
                  for(int i=0;i<size_RES_PDU;i++){
                    RES_PDU_1[i] = *(RES_PDU_TEMP +i);
                  }
                  //Temp PDU pointeri boşalt 
                  free(RES_PDU_TEMP);
                  Serial.println("RES_PDU_1: ");
                  for(int i =0;i<size_RES_PDU;i++){
                    Serial.print("/x");
                    Serial.print(RES_PDU_1[i]);
                    Serial.println(" ");
                  }
                  //Mesaj uzunluğunu belirle
                  int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_1);
                  Serial.print("Size all 1:");
                  Serial.println(size_all);
                  Serial.print("Size MBAP 1:");
                  Serial.println(elemansayisi_array(MBAP));
                  Serial.print("Size PDU 1:");
                  Serial.println(elemansayisi_array(RES_PDU_1));
                  //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                  uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_1,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_1)); 
                  //Complete frame oluştur
                  uint8_t COMPLETE_FRAME[size_all];
                  //Tempdeki değerleri Complete Frame e al
                  for(int i=0;i<size_all;i++){
                    COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP+i);
                  }
                  //Temp pointeri boşalt
                  free(COMPLETE_FRAME_TEMP);
                  //Frame bastır
                  Serial.println("COMPLETE FRAME");
                  for(int i=0;i<size_all;i++){
                    Serial.print("/x");
                    Serial.print(COMPLETE_FRAME[i], HEX);
                    Serial.print(" ");
                  }
                  //COMPLETE Frame'i client(master)'a gönder
                  Serial.println("RESPONSE_FRAME printed!");
                  //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                  send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                  Serial.println("RESPONSE_FRAME sended!");
                  /*################# END OF FUNCTION 1 ###############################*/
              }
              else if (function_code == 2){
                unsigned short start_address = (receive_message[8] << 8)| receive_message[9];               
                unsigned short quantity_of_inputs = (receive_message[10] << 8)| receive_message[11];
                Serial.print("Start Address: ");
                Serial.println(start_address);
                Serial.print("Quantity of Inputs: ");
                Serial.println(quantity_of_inputs);
                uint8_t response_pdu_length;
                uint8_t byte_count;
                //MBAP mesaj uzunluğunu bulmak için quantity of inputs sayısına bakılmalıdır.
                //Fonksiyondaki mantık burada da yapılmıştır.
                if(quantity_of_inputs >8){
                  byte_count = quantity_of_inputs /8;
                  if(quantity_of_inputs %8 != 0){
                    byte_count++;
                  }
                }else{
                  byte_count = 1;
                }
                
                //function code(1 byte) + byte count (1 byte)
                response_pdu_length = byte_count + 3;
                MBAP[4] = highByte(response_pdu_length);
                MBAP[5] = lowByte(response_pdu_length);

                //Size RES_PDU boyutunu tanımla 
                int size_RES_PDU = byte_count + 2;

                uint8_t *RES_PDU_TEMP = READ_DISCRETE_INPUTS(function_code,start_address,quantity_of_inputs);
                
                //PDU arrayini olustur
                uint8_t RES_PDU_2[size_RES_PDU];
                
                //Temp pointerindaki değerleri PDU_1 e al
                for(int i=0;i<size_RES_PDU;i++){
                  RES_PDU_2[i] = *(RES_PDU_TEMP +i);
                }
                
                //Temp PDU pointeri boşalt 
                free(RES_PDU_TEMP);

                for(int i =0;i<size_RES_PDU;i++){
                  Serial.print("/x");
                  Serial.print(RES_PDU_2[i]);
                  Serial.println(" ");
                }

                //Mesaj uzunluğunu belirle
                int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_2);

                Serial.print("Size all:");
                Serial.println(size_all);
                Serial.print("Size MBAP:");
                Serial.println(elemansayisi_array(MBAP));
                Serial.print("Size PDU:");
                Serial.println(elemansayisi_array(RES_PDU_2));

                //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_2,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_2)); 

                //Complete frame oluştur
                uint8_t COMPLETE_FRAME[size_all];

                //Tempdeki değerleri Complete Frame e al
                for(int i=0;i<size_all;i++){
                  COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP+i);
                }

                //Temp pointeri boşalt
                free(COMPLETE_FRAME_TEMP);


                //Frame bastır
                Serial.println("COMPLETE FRAME");

                for(int i=0;i<size_all;i++){
                  Serial.print("/x");
                  Serial.print(COMPLETE_FRAME[i], HEX);
                  Serial.print(" ");
                }

                //COMPLETE Frame'i client(master)'a gönder
                Serial.println("RESPONSE_FRAME printed!");
                //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                Serial.println("RESPONSE_FRAME sended!");

                /*################# END OF FUNCTION 2 ###############################*/
              }
              else if (function_code == 3){
                unsigned short start_address = (receive_message[8] << 8)| receive_message[9];               
                unsigned short quantity_of_registers = (receive_message[10] << 8)| receive_message[11]; 
                Serial.print("Start Address: ");
                Serial.println(start_address);
                Serial.print("Quantity of Registers: ");
                Serial.println(quantity_of_registers);
                //unit id(1byte) + function code(1 byte) + Byte Count(1byte) + Register Values(N*2 byte) 
                unsigned short response_t_length_f3_f4 = 1 + 2 + 2*quantity_of_registers;
                MBAP[4] = highByte(response_t_length_f3_f4);
                MBAP[5] = lowByte(response_t_length_f3_f4);
                //RES_PDU boyutu tanımla
                int size_RES_PDU = 2*quantity_of_registers + 1 + 1;
                //Fonksiyonu çağır ve geçici olarak PDU temp pointera ata
                uint8_t *RES_PDU_TEMP = READ_H_REGS(function_code, start_address, quantity_of_registers);
                //PDU arrayini oluştur.
                uint8_t RES_PDU_3[size_RES_PDU];
                Serial.println("RES_PDU generated!");
                //Temp pointerdaki değerleri PDU_3 e al
                for(int i=0;i<size_RES_PDU;i++){
                    RES_PDU_3[i] = *(RES_PDU_TEMP +i); 
                }
                //Temp pointeri boşalt 
                free(RES_PDU_TEMP);
                //Response mesaj uzunluğunu belirle
                int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_3);
                Serial.print("Size all:");
                Serial.println(size_all);
                Serial.print("Size MBAP:");
                Serial.println(elemansayisi_array(MBAP));
                Serial.print("Size PDU:");
                Serial.println(elemansayisi_array(RES_PDU_3));            
                //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_3,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_3)); 
                //Complete frame oluştur
                uint8_t COMPLETE_FRAME[size_all];
                //Pointerdaki verileri Complete frame ata 
                for(int i=0;i<(elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_3));i++){
                    COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP +i);
                }
                //Frame bastır 
                Serial.println("COMPLETE FRAME ");
                for (int i = 0; i < size_all; i++) 
                {
                  Serial.print("/x");
                  Serial.print(COMPLETE_FRAME[i], HEX);
                  Serial.print(" ");
                }
                //Temp pointeri boşalt
                free(COMPLETE_FRAME_TEMP);
                //COMPLETE Frame'i client(master)'a gönder
                Serial.println("RESPONSE_FRAME printed!");
                //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                Serial.println("RESPONSE_FRAME sended!");
                /*################# END OF FUNCTION 3 ###############################*/       
              }
              else if (function_code == 4){
                unsigned short start_address = (receive_message[8] << 8)| receive_message[9];               
                unsigned short quantity_of_input_registers = (receive_message[10] << 8)| receive_message[11];
                Serial.print("Start Address: ");
                Serial.println(start_address);
                Serial.print("Quantity of Input Registers: ");
                Serial.println(quantity_of_input_registers);
                unsigned short response_t_length_f3_f4 = 1 + 2 + 2*quantity_of_input_registers;
                MBAP[4] = highByte(response_t_length_f3_f4);
                MBAP[5] = lowByte(response_t_length_f3_f4);
                //RES_PDU boyutu tanımla
                int size_RES_PDU = 2*quantity_of_input_registers + 1 + 1;
                //Fonksiyonu çağır ve geçici olarak PDU temp pointera ata (dönen değerlerin başlangıç adresi)
                uint8_t *RES_PDU_TEMP = READ_IN_REGS(function_code, start_address, quantity_of_input_registers);
                //PDU arrayini oluştur.
                uint8_t RES_PDU_4[size_RES_PDU];
                Serial.println("RES_PDU generated!");

                //Temp pointerdaki değerleri PDU_4 e al
                for(int i=0;i<size_RES_PDU;i++){
                    RES_PDU_4[i] = *(RES_PDU_TEMP +i); 
                }
                //Temp PDU pointeri boşalt 
                free(RES_PDU_TEMP);
                
                //Response mesaj uzunluğunu belirle
                int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_4);
                Serial.print("Size all:");
                Serial.println(size_all);
                Serial.print("Size MBAP:");
                Serial.println(elemansayisi_array(MBAP));
                Serial.print("Size PDU:");
                Serial.println(elemansayisi_array(RES_PDU_4));
                //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_4,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_4)); 
                //Complete frame oluştur
                uint8_t COMPLETE_FRAME[size_all];
                //Tempdeki değerleri Complete Frame'e al
                for(int i=0;i<size_all;i++){
                  COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP+i);
                }
                //Frame bastır 
                Serial.println("COMPLETE FRAME ");
                for (int i = 0; i < size_all; i++) 
                {
                  Serial.print("/x");
                  Serial.print(COMPLETE_FRAME[i], HEX);
                  Serial.print(" ");
                }
                //Temp pointeri boşalt
                free(COMPLETE_FRAME_TEMP);
                //COMPLETE Frame'i client(master)'a gönder
                Serial.println("RESPONSE_FRAME printed!");
                //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                Serial.println("RESPONSE_FRAME sended!");
                /*################# END OF FUNCTION 4 ###############################*/
              }
              else if (function_code == 5){
                unsigned short output_address = (receive_message[8] << 8)| receive_message[9];               
                unsigned short output_value = (receive_message[10] << 8)| receive_message[11];
                Serial.print("Output Address: ");
                Serial.println(output_address);
                Serial.print("Output Value: ");
                Serial.println(output_value);
                //Bu fonksiyonda Requestin bazı byte larında mesaj tipi değişiyor. 
                //Response message uzunluğu Request message uzunluğu ile aynı olacak. 12 byte
                unsigned short response_pdu_length = 6;
                MBAP[4] = highByte(response_pdu_length);
                MBAP[5] = lowByte(response_pdu_length);
                //RES_PDU boyutunu tanımla 
                int size_RES_PDU = 5;
                //Fonksiyonu çağır ve geçici olarak PDU temp pointera ata
                uint8_t *RES_PDU_TEMP = WRITE_SINGLE_COIL(function_code,output_address,output_value);
                //PDU arrayini oluştur.
                uint8_t RES_PDU_5[size_RES_PDU];
                
                //Temp pointerdaki değerleri RES_PDU_5 e al
                for(int i =0;i<size_RES_PDU;i++){
                  RES_PDU_5[i] = *(RES_PDU_TEMP+i);
                }
                //Temp pointeri boşalt 
                free(RES_PDU_TEMP);

                int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_5);
                Serial.print("Size all:");
                Serial.println(size_all);
                Serial.print("Size MBAP:");
                Serial.println(elemansayisi_array(MBAP));
                Serial.print("Size PDU:");
                Serial.println(elemansayisi_array(RES_PDU_5));  
              
                //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_5,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_5));
                //Complete frame oluştur
                uint8_t COMPLETE_FRAME[size_all];
                //Pointerdaki verileri Complete frame ata 
                for(int i=0;i<(elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_5));i++){
                    COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP +i);
                }
                //Frame bastır 
                Serial.println("COMPLETE FRAME ");
                for (int i = 0; i < size_all; i++) 
                {
                  Serial.print("/x");
                  Serial.print(COMPLETE_FRAME[i], HEX);
                  Serial.print(" ");
                }
                //Temp pointeri boşalt
                free(COMPLETE_FRAME_TEMP);
                //COMPLETE Frame'i client(master)'a gönder
                Serial.println("RESPONSE_FRAME printed!");
                //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                Serial.println("RESPONSE_FRAME sended!");
                /*################# END OF FUNCTION 5 ###############################*/
              }
              else if (function_code == 6){
                unsigned short register_address = (receive_message[8] << 8)| receive_message[9];          
                unsigned short register_value = (receive_message[10] << 8)| receive_message[11]; 
                Serial.print("Register Address: ");
                Serial.println(register_address);
                Serial.print("Register Value: ");
                Serial.println(register_value);
                /*
                  THIS FUNCTION IS USED TO WRITE SINGLE HOLDING REGISTER IN REMOTE DEVICE
                  REQUEST IS THE ECHO OF THE RESPONSE
                  
                  REQUEST     FUNCTION CODE       1BYTE   0X06
                              REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                              REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF
                  RESPONSE    FUNCTION CODE       1BYTE   0X06
                              REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                              REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF   
                  */
                // Unit Identifier + RES_PDU = 6
                unsigned short response_pdu_length = 6; 
                MBAP[4] = highByte(response_pdu_length);
                MBAP[5] = lowByte(response_pdu_length);
                //RES_PDU boyutunu tanımla 
                int size_RES_PDU = 5;
                //Fonksiyonu çağır ve geçici olarak PDU temp pointera ata
                uint8_t *RES_PDU_TEMP = WRITE_SINGLE_REGISTER(function_code, register_address, register_value);
                //PDU arrayini oluştur.
                uint8_t RES_PDU_5[size_RES_PDU];
                
                //Temp pointerdaki değerleri RES_PDU_5 e al
                for(int i =0;i<size_RES_PDU;i++){
                  RES_PDU_5[i] = *(RES_PDU_TEMP+i);
                }
                //Temp pointeri boşalt 
                free(RES_PDU_TEMP);

                int size_all = elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_5);
                Serial.print("Size all:");
                Serial.println(size_all);
                Serial.print("Size MBAP:");
                Serial.println(elemansayisi_array(MBAP));
                Serial.print("Size PDU:");
                Serial.println(elemansayisi_array(RES_PDU_5));  
              
                //Tek framede birleştirdiktan sonra geçici olarak bit temp pointera ata
                uint8_t *COMPLETE_FRAME_TEMP = COMBINE_MBAP_PDU(MBAP,RES_PDU_5,elemansayisi_array(MBAP),elemansayisi_array(RES_PDU_5));
                //Complete frame oluştur
                uint8_t COMPLETE_FRAME[size_all];
                //Pointerdaki verileri Complete frame ata 
                for(int i=0;i<(elemansayisi_array(MBAP) + elemansayisi_array(RES_PDU_5));i++){
                    COMPLETE_FRAME[i] = *(COMPLETE_FRAME_TEMP +i);
                }
                //Frame bastır 
                Serial.println("COMPLETE FRAME ");
                for (int i = 0; i < size_all; i++) 
                {
                  Serial.print("/x");
                  Serial.print(COMPLETE_FRAME[i], HEX);
                  Serial.print(" ");
                }
                //Temp pointeri boşalt
                free(COMPLETE_FRAME_TEMP);
                //COMPLETE Frame'i client(master)'a gönder
                Serial.println("RESPONSE_FRAME printed!");
                //client.write(COMPLETE_FRAME,elemansayisi_array(COMPLETE_FRAME));
                send(socketNumber, (uint8_t*)COMPLETE_FRAME, elemansayisi_array(COMPLETE_FRAME));
                Serial.println("RESPONSE_FRAME sended!");
                /*################# END OF FUNCTION 6 ###############################*/
              }
            }
          }       
  
      if (status == SOCK_CLOSE_WAIT) 
      {
        disconnect(socketNumber);
        delay(1000);
        Serial.println("Client disconnected");
      }

      socket(socketNumber, Sn_MR_TCP, 502, 0);
      // Dinlemeye başla
      if (listen(socketNumber) == SOCK_OK) 
      {
        //Serial.println("Listening on port 502...");
      } 
      else 
      {
        Serial.println("Failed to start listening");
        while (1);
      }
      listen(socketNumber); // Soketi tekrar dinlemeye al
      delay(100);
}

//Hercule TCP client için denemeler 
//00 01 00 00 00 06 01 01 00 01 00 02 ====> Fonksiyon 1
//00 01 00 00 00 06 01 02 00 64 00 02 ====> Fonksiyon 2
//00 01 00 00 00 06 01 03 00 64 00 02 ====> Fonksiyon 3
//00 01 00 00 00 06 01 04 00 64 00 02 ====> Fonksiyon 4
//00 01 00 00 00 06 01 05 00 01 FF 00 ====> Fonksiyon 5
//00 01 00 00 00 06 01 06 00 64 00 05 ====> Fonksiyon 6 
