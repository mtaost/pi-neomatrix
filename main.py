
import display_modes.gameoflife
import display_modes.spectrumanalyzer
import display_modes.imageviewer
import display_modes.thermalcamera
import display_modes.pixelrain
import display_modes.module
import driver
import threading

def stopThread():
    global moduleThread
    if moduleThread:
        display_modes.module.Module.STOP = True
        moduleThread.join()
        moduleThread = 0
        display_modes.module.Module.STOP = False

def main():
    global moduleThread
    moduleThread = 0
    matrix_driver = driver.MatrixDriver()
    matrix_driver.set_brightness(0.1)
    while 1:
        a = input()
        if a == '1':
            stopThread()
            life = display_modes.gameoflife.GameOfLife(matrix_driver)
            moduleThread = threading.Thread(target=life.run, daemon=True)
            moduleThread.start()
        elif a == '2':
            stopThread()
            spectrum = display_modes.spectrumanalyzer.SpectrumAnalyzer(matrix_driver)
            moduleThread = threading.Thread(target=spectrum.run, daemon=True)
            moduleThread.start()
        elif a[0] == '3':
            stopThread()
            viewer = display_modes.imageviewer.ImageViewer(matrix_driver, a[2:])
            moduleThread = threading.Thread(target=viewer.run, daemon=True)
            moduleThread.start()
        elif a == '4':
            stopThread()
            camera = display_modes.thermalcamera.ThermalCamera(matrix_driver)
            moduleThread = threading.Thread(target=camera.run, daemon=True)
            moduleThread.start()
        elif a == '5':
            stopThread()
            rain = display_modes.pixelrain.PixelRain(matrix_driver)
            moduleThread = threading.Thread(target=rain.run, daemon=True)
            moduleThread.start()
        else:
            stopThread()
            exit()
        


    life = display_modes.gameoflife.GameOfLife(matrix_driver)
    
    #x = threading.Thread(target=life.run, daemon=True)
    x = threading.Thread(target=spectrum.run, daemon=True)
    x.start()
    a = ''
    while a != '0':
        a = input()
        print(a)
        if a == '0':
            display_modes.module.Module.STOP = True
            x.join()
    exit()
    # life.run()

    spectrum = display_modes.spectrumanalyzer.SpectrumAnalyzer(matrix_driver)
    spectrum.run()
    print("Hello World!")

if __name__ == "__main__":
    main()
