#TCP/IP Client with tkinter GUI
# Yahya EKİN, İlker KESER

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

label_width = 15
entry_width = 15
import struct
import socket
import random
import binascii


def READ_COILS_F(function_code, start_address, quantity_of_inputs, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    # PDU için gerekli parametreler kontrol ediliyor
    if not 0 <= int(start_address,16) <= 0xffff:
        messagebox.showerror("ERROR!", "start_address out of range (valid from 0 to 65535)")
        raise ValueError('start_address out of range (valid from 0 to 65535)')
    if not 1 <= int(quantity_of_inputs,16) <= 2000:
        messagebox.showerror("ERROR!", "quantity_of_inputs out of range (valid from 1 to 2000)")
        raise ValueError('quantity_of_inputs out of range (valid from 1 to 2000)')
    if int(start_address,16) + int(quantity_of_inputs,16) > 0x10000:
        messagebox.showerror("ERROR!", "read after end of modbus address space")
        raise ValueError('read after end of modbus address space')
    tx_pdu = struct.pack('>BHH',int(function_code,16),int(start_address,16), int(quantity_of_inputs,16));
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))

    print("TX_PDU")
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
   #print(tx_pdu)
    #Soketi açalım ve TCP ile bağlanalım
    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    
    # PDU ya MBAP Header ekleyelim.
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))

    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1 
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def READ_DISCRETE_INPUTS_F(function_code, start_address, quantity_of_inputs, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    """
    THIS FUNCTION IS USED TO READ FROM 1 TO 2000 CONTIGIOUS STATUS OF DISCRETE
    INPUTS IN A REMOTE DEVICE.    
    REQUEST     FUNCTION CODE           1BYTE   0X02
                START ADDRESS           2BYTE   0X0000 TO 0XFFFF
                QUANTITY OF INPUTS      2BYTE   0X0000 TO 0X7D0
    RESPONSE    FUNCTION CODE           1BYTE   0X02
                BYTE COUNT              1BYTE   N*
                INPUT STATUS            N* X 1BYTE  -      
    """
    # PDU için gerekli parametreler kontrol ediliyor
    if not 0 <= int(start_address,16) <= 0xffff:
        messagebox.showerror("ERROR!", "start_address out of range (valid from 0 to 65535)")
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    if not 1 <= int(quantity_of_inputs,16) <= 2000:
        messagebox.showerror("ERROR!", "quantity_of_inputs out of range (valid from 1 to 2000)")
        raise ValueError('quantity_of_inputs out of range (valid from 1 to 2000)')
    if int(start_address,16) + int(quantity_of_inputs,16) > 0x10000:
        messagebox.showerror("ERROR!", "read after end of modbus address space")
        raise ValueError('read after end of modbus address space')
    tx_pdu = struct.pack('>BHH',int(function_code,16),int(start_address,16), int(quantity_of_inputs,16));
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))
    print("TX_PDU")
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
   #print(tx_pdu)
    #Soketi açalım ve TCP ile bağlanalım
    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    
    # PDU ya MBAP Header ekleyelim.
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))

    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def READ_H_REGS(function_code, start_address, quantity_of_inputs, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    
    # PDU için gerekli parametreler kontrol ediliyor
    if not 0 <= int(start_address,16) <= 0xffff:
        messagebox.showerror("ERROR!", "start_address out of range (valid from 0 to 65535)")
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    if not 1 <= int(quantity_of_inputs,16) <= 125:
        messagebox.showerror("ERROR!", "quantity_of_registers out of range (valid from 1 to 125)")
        raise ValueError('quantity_of_registers out of range (valid from 1 to 125)')
    if int(start_address,16) + int(quantity_of_inputs,16) > 0x10000:
        messagebox.showerror("ERROR!", "read after end of modbus address space")
        raise ValueError('read after end of modbus address space')
    #transfer edilecek pdu oluşturuluyor.
    tx_pdu = struct.pack('>BHH',int(function_code,16),int(start_address,16), int(quantity_of_inputs,16));
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))
    print("TX_PDU")
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
   #print(tx_pdu)
    #Soketi açalım ve TCP ile bağlanalım
    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    
    # PDU ya MBAP Header ekleyelim.
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))
    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def READ_I_REGS(function_code, start_address, quantity_of_inputs, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    
    # PDU için gerekli parametreler kontrol ediliyor
    if not 0 <= int(start_address,16) <= 0xffff:
        messagebox.showerror("ERROR!", "reg_addr out of range (valid from 0 to 65535)")
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    if not 1 <= int(quantity_of_inputs,16) <= 125:
        messagebox.showerror("ERROR!", "quantity_of_input_registers out of range (valid from 1 to 125)")
        raise ValueError('quantity_of_input_registers out of range (valid from 1 to 125)')
    if int(start_address,16) + int(quantity_of_inputs,16) > 0x10000:
        messagebox.showerror("ERROR!", "read after end of modbus address space")
        raise ValueError('read after end of modbus address space')
    #transfer edilecek pdu oluşturuluyor.
    tx_pdu = struct.pack('>BHH',int(function_code,16),int(start_address,16), int(quantity_of_inputs,16));
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))
    print("TX_PDU")
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
   #print(tx_pdu)
    #Soketi açalım ve TCP ile bağlanalım
    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    
    # PDU ya MBAP Header ekleyelim.
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))
    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def WRITE_SINGLE_COIL_F(function_code, output_address, output_value, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    if not 0 <= int(output_address,16) <= 0xffff:
        messagebox.showerror("ERROR!", "reg_addr out of range (valid from 0 to 65535)")
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    if not (int(output_value,16) == 65280 or int(output_value,16) == 0):
        messagebox.showerror("ERROR!", "Output Value must be either 0xFF00 (ON) or 0x0000 (OFF)")
        raise ValueError('Output Value must be either 0xFF00 (ON) or 0x0000 (OFF)')
       
           

    
    tx_pdu = struct.pack('>BHH',int(function_code,16), int(output_address,16), int(output_value,16))
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))
    #To see if it is not correct.
    print("TX_PDU") 
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")

    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    #Add MBAP to PDU
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))
    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def WRITE_SINGLE_REGISTER_F(function_code, register_address, register_value, SLAVE_IP, SLAVE_PORT, UNIT_ID):
    """
    THIS FUNCTION IS USED TO WRITE SINGLE HOLDING REGISTER IN REMOTE DEVICE
    REQUEST IS THE ECHO OF THE RESPONSE
    
    REQUEST     FUNCTION CODE       1BYTE   0X06
                REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF
    RESPONSE    FUNCTION CODE       1BYTE   0X06
                REGISTER ADDRESS    2BYTE   0X0000 TO 0XFFFF
                REGISTER VALUE      2BYTE   0X0000 TO 0XFFFF   
    """
    if not 0 <= int(register_address,16) <= 0xffff:
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    if not 0 <= int(register_value,16) <= 0xffff:
        raise ValueError('reg_addr out of range (valid from 0 to 65535)')
    
    tx_pdu = struct.pack('>BHH',int(function_code,16), int(register_address,16), int(register_value,16))
    PDU_Text.set(binascii.hexlify(tx_pdu).decode('utf-8'))
   #To see if it is not correct.
    print("TX_PDU") 
    print("---------------------")
    for byte in tx_pdu:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")

    timeout = 30  # Bağlantı zaman aşımı (saniye cinsinden)
    sock, is_open = open_and_check(SLAVE_IP, SLAVE_PORT, timeout)
    if is_open:
        print("Bağlantı başarılı!")
    else:
        print("Bağlantı başarısız.")
    #Add MBAP to PDU
    transaction_id = 1 #random.randint(0, 65535)
    protocol_id = 0
    length = len(tx_pdu) + 1
    mbap = struct.pack('>HHHB', transaction_id, protocol_id, length, UNIT_ID)
    MBAP_Text.set(binascii.hexlify(mbap).decode('utf-8'))
    tx_frame = mbap + tx_pdu
    print("MBAP + TX_PDU") 
    print("---------------------")
    for byte in tx_frame:
        print(f"\\x{byte:02x}", end='')
    print()
    print("---------------------")
    #print(tx_frame)
    #TCP üzerinden tx_frame i gönderelim.
    try:
        sock.send(tx_frame)
    except socket.timeout:
        sock.close()
        print("Timeout Hatası")
    except socket.error:
        sock.close()
        print("Send Error [Gönderme Hatası]")
    
    #Slave cihazdan bize geri gelen veriyi yakalama.
    #ilk adım olarak ilk 7 byte'ı yani MBAP ı alıyoruz.
    r_buffer = b''
    while len(r_buffer) < 7:
        try:
            r_buffer += sock.recv(7 - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_mbap = r_buffer
    RE_MBAP_Text.set(binascii.hexlify(rx_mbap).decode('utf-8'))
    #Gelen MBAP'ı çözümleyip parametreleri kontrol edelim.
    (f_transaction_id, f_protocol_id, f_length, f_unit_id) = struct.unpack('>HHHB', rx_mbap)
    f_transaction_err = f_transaction_id != transaction_id
    f_protocol_err = f_protocol_id != 0
    f_length_err = f_length >= 256
    f_unit_id_err = f_unit_id != UNIT_ID
    #Hata varsa uyaralım ve TCP bağlantısını kapatalım.
    if f_transaction_err or f_protocol_err or f_length_err or f_unit_id_err:
        sock.close()
        print(f'HATA: Gelen veri:{rx_mbap}')
    #hata yoksa yola devam. Kalan PDU yu da alalım.
    #burada da kontrol yapmamız lazım. Sanırım neden hepsini ayrı fonksiyonlarda yazdıklarını anladım :\
    r_buffer = b''
    size = f_length-1
    while len(r_buffer) < size:
        try:
            r_buffer += sock.recv(size - len(r_buffer))
        except socket.timeout:
            sock.close()
            print("Timeout Hatası")
        except socket.error:
            r_buffer = b''
            print('soket hatası - buffer sıfırlandı')
        if not r_buffer:
            sock.close()
            print('[RECEIVE ERROR] Buffera gelen veri yok! Soket Kapatıldı.')
    rx_pdu = r_buffer
    RE_PDU_Text.set(binascii.hexlify(rx_pdu).decode('utf-8'))
    #PDU yu gözle kontrol için bastırıyorum.
    #print("RX PDU")
    #print("===================")
    #print(rx_pdu)
    #print("===================")
    
    #kontrol edelim
    if len(rx_pdu) < 2:
        print('PDU length is too short')
    #fonksiyon kodunu alalım
    rx_fc = rx_pdu[0]
    #exception kod olabilir
    if rx_fc >= 0x80:
        exp_code = rx_pdu[1]
        print(f'Exception code:{exp_code}')
    
    return rx_pdu

def open_and_check(host, port, timeout):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    is_open = False

    for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
        af, sock_type, proto, canon_name, sa = res
        try:
            sock = socket.socket(af, sock_type, proto)
        except socket.error:
            continue
        try:
            sock.settimeout(timeout)
            sock.connect(sa)
        except socket.error:
            sock.close()
            continue
        is_open = True
        print("\nSocket Opened!\n")
        break

    return sock, is_open

def int_to_8bit_binary(n):
    binary = ""
    while n > 0:
        binary = str(n % 2) + binary
        n = n // 2
    # Pad with leading zeros if needed
    while len(binary) < 8:
        binary = "0" + binary
    return binary

def save_port_ip():
    
    SLAVE_IP = HostIpEntry.get()
    SLAVE_PORT = int(PortEntry.get())
    UNIT_ID = int(UnitIDentry.get())
    print("Saved Connection Settings:")
    print(SLAVE_IP)
    print(SLAVE_PORT)
    print(UNIT_ID)
    IP_SET_Label_Text.set(f"IP SET:{SLAVE_IP}")

def update_entries(*args):
    selected_function = function_var.get()
    
    for widget in frame1.winfo_children():
        widget.destroy()

    
    Terminal1 = tk.Label(frame1, textvariable=TerminalText,width=label_width)
    Terminal1["bg"]="green"
    Terminal1["fg"]="#ffffff"
    Terminal1.grid(row=4, column=3, padx=0, pady=0)

    Function_SET_button = tk.Button(frame1, text="SEND DATA", command=set_function,width=entry_width,relief="groove")
    Function_SET_button.grid(row=5, column=3, padx=0, pady=0)
    
    if selected_function == "READ COILS":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width,textvariable=FunctionCodeVar)
        FunctionCodeVar.set("1")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        StartAddressLabel = tk.Label(frame1, text="Start Address:",width=label_width)
        StartAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        StartAddressEntry = tk.Entry(frame1,width=entry_width,textvariable=StartAddressVar)
        StartAddressVar.set("0")
        StartAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        QuantityOfCoilsLabel = tk.Label(frame1, text="Quantity of Coils:",width=label_width)
        QuantityOfCoilsLabel.grid(row=4, column=2, padx=0, pady=0)
        QuantityOfCoilsEntry = tk.Entry(frame1,width=entry_width, textvariable=QuantityOfCoilsVar )
        QuantityOfCoilsVar.set("2")
        QuantityOfCoilsEntry.grid(row=5, column=2, padx=0, pady=0)
    


    elif selected_function == "READ DISCRETE INPUTS":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width, textvariable=FunctionCodeVar)
        FunctionCodeVar.set("2")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        StartAddressLabel = tk.Label(frame1, text="Start Address:",width=label_width)
        StartAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        StartAddressEntry = tk.Entry(frame1,width=entry_width, textvariable=StartAddressVar)
        StartAddressVar.set("0")
        StartAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        QuantityOfInputsLabel = tk.Label(frame1, text="Quantity of Inputs:",width=label_width)
        QuantityOfInputsLabel.grid(row=4, column=2, padx=0, pady=0)
        QuantityOfInputsEntry = tk.Entry(frame1,width=entry_width, textvariable=QuantityOfInputsVar)
        QuantityOfInputsVar.set("2")
        QuantityOfInputsEntry.grid(row=5, column=2, padx=0, pady=0)
    

    elif selected_function == "READ HOLDING REGS":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width, textvariable=FunctionCodeVar)
        FunctionCodeVar.set("3")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        StartAddressLabel = tk.Label(frame1, text="Start Address:",width=label_width)
        StartAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        StartAddressEntry = tk.Entry(frame1,width=entry_width, textvariable=StartAddressVar)
        StartAddressVar.set("100")
        StartAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        QuantityOfRegistersLabel = tk.Label(frame1, text="Quantity of Registers:",width=label_width)
        QuantityOfRegistersLabel.grid(row=4, column=2, padx=0, pady=0)
        QuantityOfRegistersEntry = tk.Entry(frame1,width=entry_width, textvariable=QuantityOfRegisterVar)
        QuantityOfRegisterVar.set("2")
        QuantityOfRegistersEntry.grid(row=5, column=2, padx=0, pady=0)
    
    elif selected_function == "READ INPUT REGS":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width, textvariable=FunctionCodeVar)
        FunctionCodeVar.set("4")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        StartAddressLabel = tk.Label(frame1, text="Start Address:",width=label_width)
        StartAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        StartAddressEntry = tk.Entry(frame1,width=entry_width, textvariable=StartAddressVar)
        StartAddressVar.set("0")
        StartAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        QuantityOfInputRegistersLabel = tk.Label(frame1, text="Quantity of Input Registers:",width=label_width)
        QuantityOfInputRegistersLabel.grid(row=4, column=2, padx=0, pady=0)
        QuantityOfInputRegistersEntry = tk.Entry(frame1,width=entry_width, textvariable=QuantityOfInputRegisterVar)
        QuantityOfInputRegisterVar.set("2")
        QuantityOfInputRegistersEntry.grid(row=5, column=2, padx=0, pady=0)
    
    elif selected_function == "WRITE SINGLE COIL":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width,textvariable=FunctionCodeVar)
        FunctionCodeVar.set("5")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        OutputAddressLabel = tk.Label(frame1, text="Output Address:",width=label_width)
        OutputAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        OutputAddressEntry = tk.Entry(frame1,width=entry_width, textvariable=OutputAddressVar)
        OutputAddressVar.set("0")
        OutputAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        OutputValueLabel = tk.Label(frame1, text="Output Value:",width=label_width)
        OutputValueLabel.grid(row=4, column=2, padx=0, pady=0)
        OutputValueEntry = tk.Entry(frame1,width=entry_width, textvariable=OutputValueVar)
        OutputValueVar.set("FF00")  # Set default text
        OutputValueEntry.grid(row=5, column=2,  padx=0, pady=0)

    elif selected_function == "WRITE SINGLE REG":
        FunctionCodeLabel = tk.Label(frame1, text="Function Code:",width=label_width)
        FunctionCodeLabel.grid(row=4, column=0, padx=0, pady=0)
        FunctionCodeEntry = tk.Entry(frame1,width=entry_width, textvariable=FunctionCodeVar)
        FunctionCodeVar.set("6")  # Set default text
        FunctionCodeEntry.grid(row=5, column=0, padx=0, pady=0)

        RegisterAddressLabel = tk.Label(frame1, text="Register Address:",width=label_width)
        RegisterAddressLabel.grid(row=4, column=1, padx=0, pady=0)
        RegisterAddressEntry = tk.Entry(frame1,width=entry_width, textvariable=RegisterAddressVar)
        RegisterAddressVar.set("99")
        RegisterAddressEntry.grid(row=5, column=1, padx=0, pady=0)

        RegisterValueLabel = tk.Label(frame1, text="Register Value:",width=label_width)
        RegisterValueLabel.grid(row=4, column=2, padx=0, pady=0)
        RegisterValueEntry = tk.Entry(frame1,width=entry_width, textvariable=RegisterValueVar)
        RegisterValueVar.set("255")
        RegisterValueEntry.grid(row=5, column=2, padx=0, pady=0)

def set_function():
    print("1")
    TerminalText.set("DATA SENT!")
    int_value1 = int(FunctionCodeVar.get())
    print(int_value1)
    
    tree.delete(*tree.get_children())
    RE_MBAP_Text.set("-")
    RE_PDU_Text.set("-")
    WroteDataTextVar.set("-")
    WroteDataIndexVar.set("-")
    if int_value1 == 1: #READ COILS 0X01
        int_value2 = int(StartAddressVar.get())
        int_value3 = int(QuantityOfCoilsVar.get())
        function_code = hex(int_value1)
        start_address = hex(int_value2)
        quantity_of_coils = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(start_address)
        print(quantity_of_coils)

        rx_pdu = READ_COILS_F(function_code, start_address, quantity_of_coils, SLAVE_IP, SLAVE_PORT, UNIT_ID)
        print('---- Received PDU -------')
        print("_________________________")
        for byte in rx_pdu:
            print(f"\\x{byte:02x}", end='')
        print()
        #print(rx_pdu)
        print("_________________________")
        # extract field "byte count"
        rx_function_code = rx_pdu[0]
        print(f"RX Function Code:{rx_function_code}")
        byte_count = rx_pdu[1] #ONLY VALID FOR FUNCTİON 0X03 AND 0X04 -> FIX IT!
        print(f"RX Byte Count:{byte_count}")
        # frame with regs value
        f_regs = rx_pdu[2:]
        start_address = int(start_address,16)
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if byte_count != len(f_regs):
            print ('rx byte count mismatch')
        # allocate a reg_nb size list
        registers = [0] * byte_count
        # fill registers list with register items
        for i in range(byte_count):
            registers[i] = struct.unpack('>B', f_regs[i * 2:i * 2 + 2])[0]
            # return registers list
            print(f"Value in register[{start_address+i}]"); print(registers[i])
            print("value in Coils:")
            binary_number = int_to_8bit_binary(registers[i])
            print(binary_number)
            #I printed the values in the coils in below.
            for j in range (7, -1, -1):
                if binary_number[j] == '1':
                    print(f"Coil {7-j+start_address} = 1")
                else:
                    print(f"Coil {7-j+start_address} = 0")

            reversed_binary_number = binary_number[::-1]
        for i, bit_value in enumerate(reversed_binary_number):
            # Doğru input numarasını hesaplayın (0'dan başlayacak şekilde)
            input_number = start_address + i
            # Ağacınıza ekleyin
            tree.insert("", "end", text="COIL", values=(input_number, bit_value))

    elif int_value1 == 2: #READ DISCRETE INPUTS 0X02
        int_value2 = int(StartAddressVar.get())
        int_value3 = int(QuantityOfInputsVar.get())
        function_code = hex(int_value1)
        start_address = hex(int_value2)
        quantity_of_inputs = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(start_address)
        print(quantity_of_inputs)

        rx_pdu = READ_DISCRETE_INPUTS_F(function_code, start_address, quantity_of_inputs, SLAVE_IP, SLAVE_PORT, UNIT_ID)
        print('---- Received PDU -------')
        print("_________________________")
        for byte in rx_pdu:
            print(f"\\x{byte:02x}", end='')
        print()
        #print(rx_pdu)
        print("_________________________")
        # extract field "byte count"
        rx_function_code = rx_pdu[0]
        print(f"RX Function Code:{rx_function_code}")
        byte_count = rx_pdu[1] #ONLY VALID FOR FUNCTİON 0X03 AND 0X04 -> FIX IT!
        print(f"RX Byte Count:{byte_count}")
        # frame with regs value
        f_regs = rx_pdu[2:]
        if byte_count != len(f_regs):
            print('rx byte count mismatch')
        # allocate a reg_nb size list
        registers = [0] * byte_count
        # fill registers list with register items
        for i in range(byte_count):
            registers[i] = struct.unpack('>B', f_regs[i * 2:i * 2 + 2])[0]
            # return registers list
            start_address = int(start_address,16)
            print(f"Value in register[{start_address+i}]"); print(registers[i])
            print("Status of Inputs:")
            binary_number = int_to_8bit_binary(registers[i])
            print(binary_number)
            #I printed the values in the coils in below.
        for j in range (7, -1, -1):
            if binary_number[j] == '1':
                print(f"Input {7-j+start_address} = 1")
            else:
                print(f"Input {7-j+start_address} = 0")
        reversed_binary_number = binary_number[::-1]
        for i, bit_value in enumerate(reversed_binary_number):
            # Doğru input numarasını hesaplayın (0'dan başlayacak şekilde)
            input_number = start_address + i
            # Ağacınıza ekleyin
            tree.insert("", "end", text="DISCRETE_INPUT", values=(input_number, bit_value))

    elif int_value1 == 3: #READ HOLDING REGS 0X03
        int_value2 = int(StartAddressVar.get())
        int_value3 = int(QuantityOfRegisterVar.get())
        function_code = hex(int_value1)
        start_address = hex(int_value2)
        quantity_of_registers = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(start_address)
        print(quantity_of_registers)

        rx_pdu = READ_H_REGS(function_code,start_address,quantity_of_registers, SLAVE_IP, SLAVE_PORT, UNIT_ID)
        print('---- Received PDU -------')
        print("_________________________")
        for byte in rx_pdu:
            print(f"\\x{byte:02x}", end='')
        print()
        #print(rx_pdu)
        print("_________________________")
        # extract field "byte count"
        rx_function_code = rx_pdu[0]
        print(f"RX Function Code:{rx_function_code}")
        byte_count = rx_pdu[1] #ONLY VALID FOR FUNCTİON 0X03 AND 0X04 -> FIX IT!
        print(f"RX Byte Count:{byte_count}")
        # frame with regs value
        f_regs = rx_pdu[2:]
        quantity_of_registers = int(quantity_of_registers,16)
        start_address = int(start_address,16)
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if byte_count < 2 * quantity_of_registers or byte_count != len(f_regs):
            print ('rx byte count mismatch')
        # allocate a quantity_of_registers size list
        registers = [0] * quantity_of_registers
        # fill registers list with register items
        for i in range(quantity_of_registers):
            registers[i] = struct.unpack('>H', f_regs[i * 2:i * 2 + 2])[0]

        # return registers list
        for i in range(quantity_of_registers):
            print(f"Value in register[{start_address+i}]"); print(registers[i])
        for i, value in enumerate(registers):
            tree.insert("", "end", text="HOLDING_REGISTERS", values=(start_address+i, value))

    elif int_value1 == 4: #READ INPUT REGS 0X04
        int_value2 = int(StartAddressVar.get())
        int_value3 = int(QuantityOfInputRegisterVar.get())
        function_code = hex(int_value1)
        start_address = hex(int_value2)
        quantity_of_input_registers = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(start_address)
        print(quantity_of_input_registers)

        rx_pdu = READ_I_REGS(function_code,start_address,quantity_of_input_registers, SLAVE_IP, SLAVE_PORT, UNIT_ID)
        print('---- Received PDU -------')
        print("_________________________")
        for byte in rx_pdu:
            print(f"\\x{byte:02x}", end='')
        print()
        #print(rx_pdu)
        print("_________________________")
        rx_function_code = rx_pdu[0]
        print(f"RX Function Code:{rx_function_code}")
        byte_count = rx_pdu[1] #ONLY VALID FOR FUNCTİON 0X03 AND 0X04 -> FIX IT!
        print(f"RX Byte Count:{byte_count}")
        # frame with regs value
        f_regs = rx_pdu[2:]
        quantity_of_input_registers = int(quantity_of_input_registers,16)
        start_address = int(start_address,16)
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if byte_count < 2 * quantity_of_input_registers or byte_count != len(f_regs):
            print ('rx byte count mismatch')
        # allocate a quantity_of_input_registers size list
        registers = [0] * quantity_of_input_registers
        # fill registers list with register items
        for i in range(quantity_of_input_registers):
            registers[i] = struct.unpack('>H', f_regs[i * 2:i * 2 + 2])[0]

        # return registers list
        for i in range(quantity_of_input_registers):
            print(f"Value in register[{start_address+i}]"); print(registers[i])
        for i, value in enumerate(registers):
            tree.insert("", "end", text="INPUT_REGISTERS", values=(start_address+i, value))

    elif int_value1 == 5: #WRITE SINGLE COIL 0X05
        int_value2 = int(OutputAddressVar.get())
        int_value3 = int(OutputValueVar.get(),16)
        function_code = hex(int_value1)
        output_address = hex(int_value2)
        output_value = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(output_address)
        print(output_value)

        rx_pdu = WRITE_SINGLE_COIL_F(function_code,output_address,output_value,SLAVE_IP, SLAVE_PORT, UNIT_ID)
        coil_status = rx_pdu[3:]
        print(coil_status)
        if coil_status[0] == 255:
            print(f"Coil {output_address} ON")
            coil_val = str("ON")
        elif coil_status[0] == 0:
            print(f"Coil {output_address} ON")
            coil_val = str("OFF")
        else:
            print(f"Coil {output_address} ON")
            coil_val = str("WRONG VALUE!")

        WroteDataIndexVar.set(f"COIL[{output_address}] ")
        WroteDataTextVar.set(coil_val)

    
    elif int_value1 == 6: #WRITE SINGLE REG 0X06
        int_value2 = int(RegisterAddressVar.get())
        int_value3 = int(RegisterValueVar.get())
        function_code = hex(int_value1)
        register_address = hex(int_value2)
        register_value = hex(int_value3)
        
        SLAVE_IP = HostIpEntry.get()
        SLAVE_PORT = int(PortEntry.get())
        UNIT_ID = int(UnitIDentry.get())
        
        print("Saved Connection Settings:")
        print(SLAVE_IP)
        print(SLAVE_PORT)
        print(UNIT_ID)

        print("Saved Function Settings:")
        print(function_code)
        print(register_address)
        print(register_value)

        rx_pdu = WRITE_SINGLE_REGISTER_F(function_code, register_address,register_value, SLAVE_IP, SLAVE_PORT, UNIT_ID)
        (function_code, register_address, register_value) = struct.unpack('>BHH', rx_pdu)
        print(f"Value wrote in register[{register_address}] "); print(register_value)
        #GUI ile ilgili detaylar eklenecek.
        WroteDataIndexVar.set(f"Value wrote in register[{register_address}] ")
        WroteDataTextVar.set(register_value)

window = tk.Tk()
window.title("MODBUS TCP/IP Communication Program")

FunctionCodeVar = tk.StringVar()
StartAddressVar = tk.StringVar()
QuantityOfInputsVar = tk.StringVar()
QuantityOfCoilsVar = tk.StringVar()
QuantityOfRegisterVar = tk.StringVar()
QuantityOfInputRegisterVar = tk.StringVar()
OutputAddressVar = tk.StringVar()
OutputValueVar =tk.StringVar()
RegisterAddressVar =tk.StringVar()
RegisterValueVar = tk.StringVar()
TerminalText = tk.StringVar()

function_var = tk.StringVar()
function_var.set("READ HOLDING REGS")
function_var.trace("w", update_entries)  # This line ensures update_entries is called whenever function_var changes

function_options = ["READ COILS", "READ DISCRETE INPUTS", "READ HOLDING REGS", "READ INPUT REGS","WRITE SINGLE COIL","WRITE SINGLE REG"]
function_selector = tk.OptionMenu(window, function_var, *function_options)
function_selector.grid(row=4,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)

frame1 = tk.Frame(window)
frame1.grid(row=5,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)

ConnectionLabel = tk.Label(window, text="Connection Settings",width=label_width)
ConnectionLabel.grid(row=0,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)
ConnectionLabel["bg"]="#201188"
ConnectionLabel["fg"]="#ffffff"

HostIpLabel = tk.Label(window, text="SLAVE IP:",width=label_width)
#HostIpLabel["bg"]="#009688"
HostIpLabel.grid(row=1, column=0, padx=0, pady=0)
HostIpEntry = tk.Entry(window,width=entry_width)
HostIpEntry.insert(tk.END, "192.168.0.10")  # Set default text
HostIpEntry.grid(row=1, column=1, padx=0, pady=0)

PortLabel = tk.Label(window, text="SLAVE PORT:",width=label_width)
PortLabel.grid(row=2, column=0, padx=0, pady=0)
PortEntry = tk.Entry(window,width=entry_width)
PortEntry.insert(tk.END, "502")  # Set default text
PortEntry.grid(row=2, column=1, padx=0, pady=0)

UnitIDLabel = tk.Label(window, text="UNIT ID:",width=label_width)
UnitIDLabel.grid(row=1, column=2, padx=0, pady=0)
UnitIDentry = tk.Entry(window,width=entry_width)
UnitIDentry.insert(tk.END, "1")  # Set default text
UnitIDentry.grid(row=1, column=3, padx=0, pady=0)

IP_SET_Label_Text = tk.StringVar()
IP_SET_Label = tk.Label(window, textvariable=IP_SET_Label_Text, width=label_width,bg="green",fg="white")
IP_SET_Label.grid(row=2, column=2, padx=0, pady=0)

Ip_Port_SET_button = tk.Button(window, text="SAVE", command=save_port_ip, width=entry_width,relief="groove")
Ip_Port_SET_button.grid(row=2, column=3, padx=0, pady=0)

FunctionLabel = tk.Label(window, text="Function Settings",width=label_width)
FunctionLabel.grid(row=3,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)
FunctionLabel["bg"]="#201188"
FunctionLabel["fg"]="#ffffff"



ClientSideLabel = tk.Label(window, text=" SENT DATA: [from Client] ",width=label_width)
ClientSideLabel.grid(row=7,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)
ClientSideLabel["bg"]="#201188"
ClientSideLabel["fg"]="#ffffff"

MBAP_Text = tk.StringVar()
PDU_Text = tk.StringVar()

MBAPLabel = tk.Label(window, text="Sent MBAP:",width=label_width)
MBAPLabel.grid(row=8, column=0, padx=0, pady=0)
MBAPText = tk.Label(window, textvariable=MBAP_Text,width=label_width)
MBAPText.grid(row=8, column=1, padx=0, pady=0)
PDULabel = tk.Label(window, text="Sent PDU:",width=label_width)
PDULabel.grid(row=8, column=2, padx=0, pady=0)
PDUText = tk.Label(window, textvariable=PDU_Text,width=label_width)
PDUText.grid(row=8, column=3, padx=0, pady=0)

RE_MBAP_Text = tk.StringVar() #Received MBAP Text
RE_PDU_Text = tk.StringVar()

ServerSideLabel = tk.Label(window, text="RECEIVED DATA: [from Server]",width=label_width)
ServerSideLabel.grid(row=9,column=0,columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W)
ServerSideLabel["bg"]="#201188"
ServerSideLabel["fg"]="#ffffff"

RE_MBAPLabel = tk.Label(window, text="Received MBAP:",width=label_width, bg="orange")
RE_MBAPLabel.grid(row=10, column=0, padx=0, pady=0)
RE_MBAPText = tk.Label(window, textvariable=RE_MBAP_Text,width=label_width)
RE_MBAPText.grid(row=10, column=1, padx=0, pady=0,columnspan=3,sticky=tk.N+tk.E+tk.S+tk.W)
RE_PDULabel = tk.Label(window, text="Received PDU:",width=label_width,bg="orange")
RE_PDULabel.grid(row=11, column=0, padx=0, pady=0)
RE_PDUText = tk.Label(window, textvariable=RE_PDU_Text,width=label_width)
RE_PDUText.grid(row=11, column=1, padx=0, pady=0,columnspan=3,sticky=tk.N+tk.E+tk.S+tk.W)

WroteDataTextVar = tk.StringVar()
WroteDataIndexVar = tk.StringVar()
WroteDataLabel = tk.Label(window, text="WROTE DATA:",width=label_width, bg="yellow")
WroteDataLabel.grid(row=12, column=0, padx=0, pady=0)
WroteDataText = tk.Label(window, textvariable=WroteDataTextVar,width=label_width)
WroteDataText.grid(row=12, column=3, padx=0, pady=0)
WroteDataIndex = tk.Label(window, textvariable=WroteDataIndexVar,width=label_width)
WroteDataIndex.grid(row=12, column=1, columnspan=2, padx=0, pady=0,sticky=tk.N+tk.E+tk.S+tk.W)


tree = ttk.Treeview(window)
tree["columns"] = (0, 1)  # Sütun indeksleri
tree.column(0, anchor=tk.W, width=60)
tree.column(1, anchor=tk.W, width=60)

tree.heading(0, text="Index")
tree.heading(1, text="Value")
tree.grid(row=13, column=0, columnspan=4, sticky=tk.N+tk.E+tk.S+tk.W,padx=12,pady=12)


update_entries()  # Initial call to populate entries based on default selection
window.mainloop()


