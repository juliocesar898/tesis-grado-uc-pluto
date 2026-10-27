"""
=============================================================================
TRANSMISOR DE MODULACIONES DIGITALES EN TIEMPO REAL (PLUTO+ TX1)
Tesis de Grado en Ingeniería en Telecomunicaciones - Universidad de Carabobo
Reconocimiento de Modulaciones Digitales mediante IA y SDR
=============================================================================
Este script genera ráfagas de 1024 muestras de modulaciones digitales
reales (BPSK, QPSK, 8PSK, 16QAM, Tono Senoidal o Ráfaga Golden RadioML)
con filtrado y conformado de pulso Nyquist (RRC, SPS=8) para coincidir
con el ancho de banda y características del clasificador CNN DeepSignal.
"""

import sys
import os
import time
import argparse
import numpy as np
from pathlib import Path

# 1. Carga segura del controlador dinámico libiio en Windows
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
    print("❌ ERROR: La librería 'pyadi-iio' no está instalada en este entorno virtual.")
    print("Ejecuta: pip install pyadi-iio numpy")
    sys.exit(1)


def rrc_filter(num_taps=65, beta=0.35, sps=8):
    """
    Genera los coeficientes de un filtro Root Raised Cosine (RRC)
    para conformado de pulsos Nyquist digital con SPS=8.
    """
    t = np.arange(-num_taps // 2 + 1, num_taps // 2 + 1) / float(sps)
    h = np.zeros(num_taps, dtype=float)
    for i, ti in enumerate(t):
        if np.isclose(ti, 0.0):
            h[i] = 1.0 - beta + (4.0 * beta / np.pi)
        elif np.isclose(np.abs(ti), 1.0 / (4.0 * beta)):
            h[i] = (beta / np.sqrt(2.0)) * (
                ((1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta)))
                + ((1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta)))
            )
        else:
            numerador = np.sin(np.pi * ti * (1.0 - beta)) + 4.0 * beta * ti * np.cos(
                np.pi * ti * (1.0 + beta)
            )
            denominador = np.pi * ti * (1.0 - (4.0 * beta * ti) ** 2)
            h[i] = numerador / denominador
    return h / np.sqrt(np.sum(h**2))


def cargar_muestra_golden_radioml(nombre_mod="QPSK"):
    """
    Carga una muestra oficial de alta SNR directamente desde los archivos .npy
    exportados de RadioML o desde el HDF5 para referencia patrón absoluta.
    """
    nombre_mod = nombre_mod.upper()
    # 1. Probar carga directa desde golden_samples/*.npy (sin requerir h5py)
    npy_path = Path(__file__).resolve().parent / "golden_samples" / f"{nombre_mod}.npy"
    if npy_path.exists():
        try:
            samples_arr = np.load(str(npy_path))
            idx = np.random.randint(0, len(samples_arr))
            X_val = samples_arr[idx]
            sig = X_val[:, 0] + 1j * X_val[:, 1]
            max_amp = np.max(np.abs(sig))
            sig_norm = (sig / (max_amp if max_amp > 0 else 1.0)) * 0.75
            samples_tx = np.int16(sig_norm.real * 32767) + 1j * np.int16(sig_norm.imag * 32767)
            print(f"[GOLDEN] Muestra RadioML ({nombre_mod}) cargada desde {npy_path.name}")
            return samples_tx
        except Exception as e_npy:
            print(f"Aviso leyendo .npy: {e_npy}")

    # 2. Alternativa: leer directamente de HDF5 si h5py está presente
    posibles_paths = [
        Path("../tesis-grado-uc-backend/dataset/GOLD_XYZ_OSC.0001_1024.hdf5"),
        Path("dataset/GOLD_XYZ_OSC.0001_1024.hdf5")
    ]
    for p in posibles_paths:
        if p.exists():
            try:
                import h5py
                with h5py.File(str(p), "r") as f:
                    clases = [
                        'OOK', '4ASK', '8ASK', 'BPSK', 'QPSK', '8PSK', '16PSK', '32PSK',
                        '16APSK', '32APSK', '64APSK', '128APSK', '16QAM', '32QAM', '64QAM',
                        '128QAM', '256QAM', 'AM-SSB-WC', 'AM-SSB-SC', 'AM-DSB-WC', 'AM-DSB-SC',
                        'FM', 'GMSK', 'OQPSK'
                    ]
                    c_idx = clases.index(nombre_mod)
                    Y = f['Y'][:]
                    Z = f['Z'][:]
                    indices = np.where((np.argmax(Y, axis=1) == c_idx) & (Z[:, 0] >= 18))[0]
                    if len(indices) > 0:
                        s_idx = indices[np.random.randint(0, min(50, len(indices)))]
                        X_val = f['X'][s_idx]
                        sig = X_val[:, 0] + 1j * X_val[:, 1]
                        sig_norm = (sig / np.max(np.abs(sig))) * 0.75
                        samples_tx = np.int16(sig_norm.real * 32767) + 1j * np.int16(sig_norm.imag * 32767)
                        return samples_tx
            except Exception as e:
                print(f"Aviso: No se pudo leer muestra Golden de RadioML: {e}")
    return None


def generar_rafaga_modulacion(tipo="QPSK", total_muestras=1024, sps=8):
    """
    Genera un vector continuo de exactamente 1024 muestras complejas IQ
    con tasa de sobremuestreo SPS=8 para coincidir con RadioML 2018.
    """
    tipo = tipo.upper()

    if tipo.startswith("GOLDEN_"):
        nombre_base = tipo.replace("GOLDEN_", "")
        golden = cargar_muestra_golden_radioml(nombre_base)
        if golden is not None:
            return golden
        print(f"Dataset no disponible para {nombre_base}; sintetizando matemáticamente...")
        tipo = nombre_base

    num_simbolos = total_muestras // sps  # 128 símbolos para SPS=8 en 1024 muestras
    
    if tipo == "BPSK":
        bits = np.random.randint(0, 2, num_simbolos)
        simbolos = 2 * bits - 1 + 0j

    elif tipo == "QPSK":
        # Constelación QPSK ortogonal simétrica
        bits_i = 2 * np.random.randint(0, 2, num_simbolos) - 1
        bits_q = 2 * np.random.randint(0, 2, num_simbolos) - 1
        simbolos = (bits_i + 1j * bits_q) / np.sqrt(2)

    elif tipo == "8PSK":
        fases = np.random.randint(0, 8, num_simbolos) * (2 * np.pi / 8)
        simbolos = np.exp(1j * fases)

    elif tipo == "16QAM":
        puntos = np.array([-3, -1, 1, 3])
        i_parts = np.random.choice(puntos, num_simbolos)
        q_parts = np.random.choice(puntos, num_simbolos)
        simbolos = (i_parts + 1j * q_parts) / np.sqrt(10)

    elif tipo in ["TONO", "CARRIER"]:
        # Tono senoidal puro con desplazamiento de 100 kHz
        fs = 2e6
        f_offset = 100e3
        t = np.arange(total_muestras)
        tono = 0.75 * np.exp(1j * 2 * np.pi * f_offset * t / fs)
        samples_tx = np.int16(tono.real * 32767) + 1j * np.int16(tono.imag * 32767)
        return samples_tx

    else:
        raise ValueError(f"Modulación '{tipo}' no soportada.")

    # Conformado de pulso Nyquist RRC con SPS=8 y longitud de 65 taps
    filtro = rrc_filter(num_taps=65, beta=0.35, sps=sps)
    
    # Sobremuestreo insertando ceros
    simbolos_upsampled = np.zeros(num_simbolos * sps, dtype=complex)
    simbolos_upsampled[::sps] = simbolos
    
    # Convolución circular para garantizar continuidad estricta en búfer cíclico
    rep_up = np.tile(simbolos_upsampled, 3)
    filt_out = np.convolve(rep_up, filtro, mode="same")
    signal_filtrada = filt_out[len(simbolos_upsampled):2*len(simbolos_upsampled)]

    # Normalización para no saturar los conversores DAC del AD9363
    max_val = np.max(np.abs(signal_filtrada))
    if max_val > 0:
        signal_norm = (signal_filtrada / max_val) * 0.75
    else:
        signal_norm = signal_filtrada

    samples_tx = np.int16(signal_norm.real * 32767) + 1j * np.int16(signal_norm.imag * 32767)
    return samples_tx


def main():
    parser = argparse.ArgumentParser(description="Transmisor de Modulaciones Digitales Pluto+ (Tesis UC)")
    parser.add_argument("--ip", default="ip:192.168.2.1", help="URI IP del dispositivo Pluto+")
    parser.add_argument("--freq", type=float, default=2480e6, help="Frecuencia central en Hz (default: 2.480 GHz)")
    parser.add_argument("--rate", type=float, default=2e6, help="Tasa de muestreo en SPS (default: 2 MSPS)")
    parser.add_argument("--gain", type=int, default=-20, help="Ganancia hardware TX en dB")
    parser.add_argument("--mod", default=None, help="Modulación inicial: BPSK, QPSK, 8PSK, 16QAM, TONO, GOLDEN_QPSK")
    args = parser.parse_args()

    print("====================================================================")
    print("📡 TRANSMISOR DE MODULACIONES DIGITALES OTA (PLUTO+ TX1)")
    print("Universidad de Carabobo - Proyecto de Grado DeepSignal AMC")
    print("====================================================================")
    print(f"🔗 Conectando a Pluto+ en [{args.ip}]...")

    sdr = None
    try:
        sdr = adi.Pluto(args.ip)
        sdr.tx_lo = int(args.freq)
        sdr.sample_rate = int(args.rate)
        sdr.tx_rf_bandwidth = int(args.rate)
        sdr.tx_cyclic_buffer = True
        sdr.tx_hardwaregain_chan0 = int(args.gain)

        print(f"✅ Hardware configurado exitosamente:")
        print(f"   • Frecuencia TX: {args.freq / 1e6:.3f} MHz ({args.freq / 1e9:.3f} GHz)")
        print(f"   • Tasa Muestreo: {args.rate / 1e6:.2f} MSPS")
        print(f"   • Ganancia TX:   {args.gain} dB (Potencia de Laboratorio)")
        print(f"   • Pulso Nyquist: RRC (Roll-off 0.35, SPS=8)")
        print(f"   • Búfer Cíclico: Habilitado (1024 Muestras Complejas)")
        print("--------------------------------------------------------------------")

        opciones_mod = {
            "1": "BPSK",
            "2": "QPSK",
            "3": "8PSK",
            "4": "16QAM",
            "5": "TONO",
            "6": "GOLDEN_QPSK",
            "7": "GOLDEN_BPSK",
            "8": "GOLDEN_8PSK",
            "9": "GOLDEN_16QAM"
        }

        mod_actual = args.mod.upper() if args.mod else "QPSK"
        if mod_actual not in ["BPSK", "QPSK", "8PSK", "16QAM", "TONO", "GOLDEN_QPSK", "GOLDEN_BPSK", "GOLDEN_8PSK", "GOLDEN_16QAM"]:
            mod_actual = "QPSK"

        def transmitir_modulacion(nombre_mod):
            try:
                sdr.tx_destroy_buffer()
            except Exception:
                pass
            time.sleep(0.08)  # Pequeña pausa para que libiio libere los descriptores del DMA
            muestras = generar_rafaga_modulacion(nombre_mod, total_muestras=1024, sps=8)
            try:
                sdr.tx(muestras)
            except Exception as e_tx:
                time.sleep(0.15)
                sdr.tx(muestras)
            print(f"\n🚀 [EMITIENDO AL AIRE] Modulación: >>> {nombre_mod} <<< en {args.freq/1e9:.3f} GHz")
            print("   (Observa en el Dashboard Web la clasificación y constelación en vivo)")

        transmitir_modulacion(mod_actual)

        print("\nMenú Interactivo de Transmisión (Presiona el número y Enter para alternar):")
        print(" --- Modulaciones Sintéticas (DSP Local) ---")
        print(" [1] BPSK")
        print(" [2] QPSK (Conformado RRC con SPS=8)")
        print(" [3] 8PSK")
        print(" [4] 16QAM")
        print(" [5] Tono Continuo (Desplazamiento +100 kHz)")
        print(" --- Modulaciones Golden de Referencia (Patrones Exactos RadioML) ---")
        print(" [6] Ráfaga QPSK Golden (RadioML Patrón)")
        print(" [7] Ráfaga BPSK Golden (RadioML Patrón)")
        print(" [8] Ráfaga 8PSK Golden (RadioML Patrón)")
        print(" [9] Ráfaga 16QAM Golden (RadioML Patrón)")
        print(" [q] Salir")
        print("--------------------------------------------------------------------")

        while True:
            try:
                entrada = input("Elige modulación para emitir [1-9 / q]: ").strip()
                if entrada.lower() == "q":
                    break
                if entrada in opciones_mod:
                    nueva_mod = opciones_mod[entrada]
                    transmitir_modulacion(nueva_mod)
                else:
                    print("Opción inválida. Selecciona un número del 1 al 9, o 'q'.")
            except (KeyboardInterrupt, EOFError):
                break

    except KeyboardInterrupt:
        print("\n🛑 Transmisión cancelada por el usuario.")
    except Exception as e:
        print(f"\n❌ Error en enlace con Pluto+ SDR: {e}")
    finally:
        if sdr is not None:
            try:
                sdr.tx_destroy_buffer()
            except Exception:
                pass
            del sdr
            print("🔌 Búfer cíclico destruido y transceptor Pluto+ liberado con éxito.")
        print("====================================================================")


if __name__ == "__main__":
    main()
