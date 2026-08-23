import numpy as np
import os
import sys
import time

# 1. Manejo seguro de la DLL de Windows de libiio (Misma estructura de laboratorio)
posibles_rutas = [
    r"C:\Program Files\Analog Devices\libiio",
    r"C:\Program Files (x86)\Analog Devices\libiio",
    r"C:\Program Files\libiio",
    r"C:\Program Files (x86)\libiio",
    r"C:\libiio",
]

for ruta in posibles_rutas:
    if os.path.exists(ruta):
        try:
            os.add_dll_directory(ruta)
        except Exception:
            pass

try:
    import adi
except ImportError:
    print("❌ ERROR: La librería 'pyadi-iio' no está instalada en este entorno.")
    sys.exit(1)

def iniciar_transmisor():
    print("==================================================")
    print("📡 TRANSMISOR DE PRUEBA (PLUTO+ TX1)")
    print("==================================================")
    
    sdr = None
    try:
        print("🔄 Conectando al Pluto+ SDR...")
        sdr = adi.Pluto("ip:192.168.2.1")
        
        # 2. Configuración de Radiofrecuencia para Transmisión (TX)
        # Usaremos la misma frecuencia limpia que validamos antes: 2.480 GHz (Canal 39 BLE)
        sdr.tx_lo = int(2480e6)          # Frecuencia central: 2.480 GHz
        sdr.sample_rate = int(2e6)       # Tasa de muestreo: 2 MSPS
        sdr.tx_cyclic_buffer = True      # Bucle cíclico: repite la señal infinitamente sin gastar CPU
        
        # 3. Configuración de Ganancia y Canales TX
        # Configuramos una potencia moderada (ej. -20 dB) para pruebas cercanas y seguras de hardware
        sdr.tx_hardwaregain_chan0 = -20  # Ganancia de transmisión en canal TX1 (en dB, valores negativos reducen potencia)
        
        print("✅ ¡Hardware configurado en Modo Transmisión (TX1)!")
        
        # 4. Generación de la Portadora (Tono sinusoidal simple en banda base)
        # Al transmitir un tono fijo, veremos un pico agudo y brillante exacto en el espectro.
        num_muestras = 1024
        t = np.arange(num_muestras)
        frecuencia_tono = 100e3  # Desplazamiento de 100 kHz respecto a la portadora central
        
        # Generar señal compleja senoidal (I + jQ)
        tono_iq = 0.5 * np.exp(1j * 2 * np.pi * frecuencia_tono * t / sdr.sample_rate)
        
        # Convertir a formato entrelazado que exige el driver de transmisión de pyadi-iio
        # Pluto espera un arreglo donde la parte real e imaginaria se envíen correctamente
        samples_tx = np.int16(tono_iq.real * 32767) + 1j * np.int16(tono_iq.imag * 32767)
        
        print("🚀 Emitiendo portadora continua al aire por TX1...")
        print("⏳ Manteniendo transmisión activa. Presiona Ctrl+C para detener.\n")
        
        # Enviar buffer cíclico al hardware
        sdr.tx(samples_tx)
        
        # Bucle pasivo para mantener el script vivo mientras el hardware transmite por sí solo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Transmisión detenida por el usuario.")
    except Exception as e:
        print(f"\n❌ Error crítico en el transmisor: {e}")
    finally:
        if sdr is not None:
            try:
                # Desactivar buffer cíclico y limpiar estado TX de forma segura
                sdr.tx_destroy_buffer()
            except:
                pass
            del sdr
            print("🔌 Pluto+ TX liberado con éxito.")
        print("==================================================")

if __name__ == "__main__":
    iniciar_transmisor()