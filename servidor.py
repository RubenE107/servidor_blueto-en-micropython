import bluetooth
import time
from bluetooth import BLE
from machine import Pin

SERVICE_UUID = bluetooth.UUID("6e400001-b5a3-f393-e0a9-e50e24dcca9e")
CHAR_UUID = bluetooth.UUID("6e400003-b5a3-f393-e0a9-e50e24dcca9e")

ble = BLE()
ble.active(True)

conn_handle = None
char_handle = None

led = Pin("LED", Pin.OUT) if hasattr(Pin, "LED") else Pin(2, Pin.OUT)  # LED integrado o GPIO 2

def try_reconnect():
    global conn_handle, char_handle
    conn_handle = None
    char_handle = None
    print("🔄 Reintentando conexión BLE...")
    led.on()  # 🔵 LED encendido al buscar
    ble.gap_scan(30000)

def ble_irq(event, data):
    global conn_handle, char_handle

    if event == 5:  # _IRQ_SCAN_RESULT
        addr_type, addr, adv_type, rssi, adv_data = data
        if SERVICE_UUID in decode_services(adv_data):
            print("🔍 Dispositivo encontrado:", addr)
            ble.gap_scan(None)
            ble.gap_connect(addr_type, addr)

    elif event == 7:  # _IRQ_PERIPHERAL_CONNECT
        conn_handle, _, _ = data
        print("✅ Conectado. Buscando servicios...")
        led.off()  # 🔲 Apagar LED al conectar
        ble.gattc_discover_services(conn_handle)

    elif event == 8:  # _IRQ_PERIPHERAL_DISCONNECT
        print("🔌 Desconectado del servidor. Reintentando...")
        try_reconnect()

    elif event == 9:  # _IRQ_GATTC_SERVICE_RESULT
        start_handle, end_handle, uuid = data[1], data[2], data[3]
        print("📘 Servicio encontrado:")
        print("   UUID:", uuid)
        print("   Handles:", start_handle, "-", end_handle)

        if uuid == SERVICE_UUID:
            ble.gattc_discover_characteristics(conn_handle, start_handle, end_handle)

    elif event == 11:  # _IRQ_GATTC_CHARACTERISTIC_RESULT
        if len(data) >= 4:
            char_handle = data[2]
            char_uuid = data[4]
            print("🔧 Característica encontrada:")
            print("   UUID:", char_uuid)
            print("   Handle:", char_handle)

            if char_uuid == CHAR_UUID:
                print("📤 Subscribiendo a notificaciones y enviando saludo...")
                ble.gattc_write(conn_handle, char_handle + 1, b'\x01\x00', 1)
                ble.gattc_write(conn_handle, char_handle, b'Hola desde cliente', 1)

    elif event == 18:  # _IRQ_GATTC_NOTIFY
        conn, value_handle, notify_data = data
        try:
            msg = bytes(notify_data).decode()
            print("📨 Notificación recibida:", msg)
        except Exception as e:
            print("⚠️ Error al decodificar:", e)
            print("Datos crudos:", list(bytes(notify_data)))


def decode_services(adv_data):
    services = []
    i = 0
    while i < len(adv_data):
        length = adv_data[i]
        if length == 0:
            break
        type = adv_data[i + 1]
        if type in [0x06, 0x07]:  # 128-bit UUIDs
            for j in range((length - 1) // 16):
                uuid = bluetooth.UUID(adv_data[i+2 + j*16:i+18 + j*16])
                services.append(uuid)
        i += 1 + length
    return services

# 🔁 Bucle principal
ble.irq(ble_irq)

while True:
    if conn_handle is None:
        print("📡 Escaneando BLE...")
        led.on()  # 🔵 LED encendido mientras busca
        ble.gap_scan(30000)
    time.sleep(1)

