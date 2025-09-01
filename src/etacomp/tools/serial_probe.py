import sys, time
import serial
from serial.tools import list_ports

def main():
    ports = [p.device for p in list_ports.comports()]
    print("Ports détectés:", ports)
    if len(sys.argv) < 2:
        print("Usage: python tools/serial_probe.py COMx [baud]")
        sys.exit(1)
    port = sys.argv[1]
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 4800
    print(f"Ouvre {port} @ {baud} ...")
    ser = serial.Serial(port=port, baudrate=baud, timeout=0.2)
    try:
        ser.setDTR(True); ser.setRTS(True)
    except Exception:
        pass
    time.sleep(1.0)
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception:
        pass

    print("Lecture 5 secondes (CR/LF)…")
    end = time.time() + 5
    buf = bytearray()
    while time.time() < end:
        n = ser.in_waiting
        if n:
            chunk = ser.read(n)
            buf.extend(chunk.replace(b"\r\n", b"\n"))
            while b"\n" in buf or b"\r" in buf:
                # normalise CRLF->LF puis traite CR
                buf[:] = buf.replace(b"\r\n", b"\n")
                if b"\n" in buf:
                    line, _, rest = bytes(buf).partition(b"\n")
                else:
                    line, _, rest = bytes(buf).partition(b"\r")
                buf[:] = rest
                text = line.decode(errors="ignore").strip()
                if text:
                    print("LIGNE:", repr(text))
        else:
            time.sleep(0.01)
    ser.close()

if __name__ == "__main__":
    main()
