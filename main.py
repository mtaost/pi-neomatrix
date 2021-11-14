import display_modes.gameoflife
import display_modes.spectrumanalyzer
import driver

def main():
    matrix_driver = driver.MatrixDriver()
    matrix_driver.set_brightness(0.10)
    life = display_modes.gameoflife.GameOfLife(matrix_driver)
    # life.run()

    spectrum = display_modes.spectrumanalyzer.SpectrumAnalyzer(matrix_driver)
    spectrum.run()
    print("Hello World!")

if __name__ == "__main__":
    main()
