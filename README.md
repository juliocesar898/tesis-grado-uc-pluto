# Control de Transmisión con Pluto+ SDR — Tesis de Grado UC

Este proyecto contiene los scripts necesarios para controlar y transmitir señales de radiofrecuencia (RF) utilizando el transceptor de software definido por radio (SDR) **Analog Devices ADALM-PLUTO (Pluto+)** mediante la API de Python `pyadi-iio`.

El objetivo actual del repositorio es proporcionar scripts de prueba funcionales para validar la transmisión de portadoras y señales en banda base mediante la interfaz de red del dispositivo. En particular, el archivo principal es [tx_carrier.py](tx_carrier.py).

---

## 🛠️ Requisitos de Hardware y Software

### 1. Hardware
*   **SDR Pluto+** (o ADALM-PLUTO original) conectado por USB (modo Ethernet emulado) o cable de red RJ45.
*   Dirección IP fija configurada en el dispositivo (por defecto en este script: `192.168.2.1`).
*   Antena adecuada para la banda ISM de $2.4$ GHz conectada al puerto de transmisión **TX1**.

### 2. Software (Windows)
*   **Controladores del ADALM-Pluto** instalados en Windows.
*   **libiio (DLL de Analog Devices)**:
    El script busca las librerías dinámicas necesarias en directorios comunes del sistema, como:
    *   `C:\Program Files\Analog Devices\libiio`
    *   `C:\Program Files\libiio`
*   **Python 3.9+** instalado en su entorno virtual.

---

## 📦 Instalación

1.  Clona el repositorio o descarga el código en tu directorio de trabajo.
2.  Crea y activa un entorno virtual de Python:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```
3.  Instala las dependencias necesarias:
    ```bash
    pip install numpy pyadi-iio
    ```

> ⚠️ **Nota para Windows:** Asegúrate de instalar la herramienta oficial de [libiio de Analog Devices](https://github.com/analogdevicesinc/libiio/releases) para que la biblioteca física `libiio.dll` esté disponible en el sistema.

---

## 🚀 Uso del Transmisor de Prueba

El script principal [tx_carrier.py](tx_carrier.py) genera y emite una portadora continua (tono de prueba) desplazada $+100$ kHz con respecto a la frecuencia central de transmisión.

Para iniciar la transmisión, ejecuta:

```bash
python tx_carrier.py
```

### Parámetros Configurables en el Script
Dentro de [tx_carrier.py](tx_carrier.py) se configuran los siguientes parámetros clave para la transmisión segura en laboratorio:

*   **Frecuencia Central (`tx_lo`):** `$2480\text{e}6$` ($2.480$ GHz, correspondiente al canal 39 de Bluetooth Low Energy - BLE, libre de interferencias mayores).
*   **Tasa de Muestreo (`sample_rate`):** `$2\text{e}6$` ($2$ MSPS).
*   **Atenuación de TX (`tx_hardwaregain_chan0`):** $-20$ dB (atenuación moderada para evitar saturación del receptor y daño de hardware cercano).
*   **Búfer Cíclico (`tx_cyclic_buffer`):** Habilitado para mantener la portadora de manera continua sin sobrecargar el procesador del host.

Para detener la emisión, pulsa `Ctrl+C` en la terminal. El programa liberará de forma segura el búfer y desconectará el dispositivo para que esté disponible en futuros procesos.

---

## 📂 Archivos del Repositorio

*   [tx_carrier.py](tx_carrier.py): Script de transmisión de portadora en banda base.
*   [.gitignore](.gitignore): Exclusiones de Git para reportes de Python, entornos virtuales y capturas binarias de señales `.iq`.

---

## 📝 Próximos Pasos (Tesis)
*   [ ] Implementar un receptor homólogo de portadora para medir pérdida de trayectoria.
*   [ ] Generar modulaciones digitales más complejas (BPSK/QPSK) para evaluar tasa de error de bit (BER).
*   [ ] Diseñar la secuencia de tramas y el protocolo de control de capa física.
