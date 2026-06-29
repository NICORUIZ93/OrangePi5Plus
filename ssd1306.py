import smbus


class SSD1306_Display:
    """
        Class used to drive a SSD1306 OLED Display
        over a I2C Bus
    """

    def __init__(self, bus=0, addr=0x3C, width=128, height=64):
        """
            Class init function
                bus: I2C bus number to use (default: 0)
                addr: I2C address of the display (default 0x3C)
                width: width of display in pixel (default 128)
                height: height of display in pixel (default 64)
        """
        self.bus = smbus.SMBus(bus)
        self.DISPLAY_ADDRESS = addr

        # Registers
        self.COMMAND_REG = 0x00      # Or 0x80 ?
        self.DATA_REG = 0x40

        self.DISPLAY_WIDTH = width
        self.DISPLAY_HEIGHT = height
        self.DISPLAY_PAGE_SIZE = 8
        self.DISPLAY_PAGE_LENGTH = self.DISPLAY_PAGE_SIZE * self.DISPLAY_WIDTH

        # Commands
        self.DISPLAY_OFF = 0xAE
        self.DISPLAY_ON = 0xAF
        self.DISPLAY_SETDISPLAYCLOCKDIV = 0xD5
        self.DISPLAY_SETMULTIPLEX = 0xA8
        self.DISPLAY_SETDISPLAYOFFSET = 0xD3
        self.DISPLAY_SETSTARTLINE = 0x40
        self.DISPLAY_CHARGEPUMP = 0x8D
        self.DISPLAY_MEMORYMODE = 0x20
        self.DISPLAY_SEGREMAP = 0xA0
        self.DISPLAY_COMSCANDEC = 0xC8
        self.DISPLAY_INV_DISPLAY_OFF = 0xA6
        self.DISPLAY_INV_DISPLAY_ON = 0xA7
        self.DISPLAY_ALL_ON_OFF = 0xA4
        self.DISPLAY_ALL_ON_ON = 0xA5
        self.DISPLAY_SETVCOMDETECT = 0xDB
        self.DISPLAY_SETPRECHARGE = 0xD9
        self.DISPLAY_SETCONTRAST = 0x81
        self.DISPLAY_SETCOMPINS = 0xDA
        self.DISPLAY_SET_COL_ADDR = 0x21
        self.DISPLAY_SET_PAGE_ADDR = 0x22

        # Adde Mode
        self.HORIZONTAL_ADDRESSING = 0x00
        self.PAGE_ADDRESSING = 0x02

        self.BUFFER_SIZE = self.DISPLAY_WIDTH * self.DISPLAY_HEIGHT / 8
        self.BUFFER = [0x0] * self.BUFFER_SIZE

    # Comminications functions

    def writeCommand(self, comm):
        """
            Send a Command com to the display
        """
        self.bus.write_byte_data(self.DISPLAY_ADDRESS, self.COMMAND_REG, comm)

    def writeCommandList(self, comms):
        """
            Send all Commands in the given comms list to the display
        """
        for comm in comms:
            self.bus.write_byte_data(
                self.DISPLAY_ADDRESS, self.COMMAND_REG, comm)

    def writeData(self, byte):
        """
            Send a Byte of data to the display
        """
        self.bus.write_byte_data(slef.DISPLAY_ADDRESS, self.DATA_REG, byte)

    def writeBlockData(self, data):
        """
            Send a Block of data to the display
            data is a array of Bytes (max length=32)
        """
        self.bus.write_i2c_block_data(
            self.DISPLAY_ADDRESS, self.DATA_REG, data)

    # Helper functions

    def setContrast(self, con):
        """
            Valid value 0x0 to 0xFF
        """
        self.writeCommand(self.DISPLAY_SETCONTRAST)       # 0x81
        self.writeCommand(con)

    def setColAddress(self, col=0):
        """
            Set the horizontal writing pointer of the SSD8306
        """
        self.writeCommand(self.DISPLAY_SET_COL_ADDR)        # 0x21
        # Column start address
        self.writeCommand(col)
        self.writeCommand(self.DISPLAY_WIDTH-1)  # Column end address

    def setPageAddress(self, page=0):
        """
            Set the page of the writing pointer of the SSD8306
        """
        self.writeCommand(self.DISPLAY_SET_PAGE_ADDR)     # 0x22
        self.writeCommand(page)                           # Start Page address
        # End Page Address
        self.writeCommand((self.DISPLAY_HEIGHT/self.DISPLAY_PAGE_SIZE)-1)

    def initDisplay(self):
        """
            Default initialization of the SSD8306
            for a 128x64 screen
        """
        self.writeCommandList([
            self.DISPLAY_OFF,

            self.DISPLAY_SETMULTIPLEX,
            0x3F,

            self.DISPLAY_SETDISPLAYOFFSET,
            0x0,

            self.DISPLAY_SETSTARTLINE | 0x00,    # Start Line #0

            self.DISPLAY_MEMORYMODE,             # 0x20
            0x00,                                # Auto Horizontal addressing

            self.DISPLAY_SEGREMAP | 0x1,         # rotate screen 180

            self.DISPLAY_COMSCANDEC,             # rotate screen 180

            self.DISPLAY_SETCOMPINS,             # 0xDA
            0x12,                                # COM sequence (Split)

            self.DISPLAY_SETCONTRAST,            # 0x81
            0xFF,

            self.DISPLAY_ALL_ON_OFF,             # 0xA4

            self.DISPLAY_INV_DISPLAY_OFF,        # 0xA6

            self.DISPLAY_SETDISPLAYCLOCKDIV,     # 0xD5
            0x80,

            self.DISPLAY_CHARGEPUMP,             # 0x8D
            0x14,                                # Enable Charge Pump (Vcc)

            self.DISPLAY_SETPRECHARGE,           # 0xD9
            0xF1,

            self.DISPLAY_SETVCOMDETECT,          # 0xDB
            0x40,

            self.DISPLAY_ON                       # 0xAF

        ])

    def _displayBuffer(self):
        """
            Byte by byte data transfer
        """
        self.setColAddress()
        self.setPageAddress()
        for b in self.BUFFER:
            self.writeData(b)

    def displayBuffer(self):
        """
            32 bytes block data transfer
        """
        self.setColAddress()
        self.setPageAddress()
        for i in range(0, len(self.BUFFER), 32):
            self.writeBlockData(self.BUFFER[i:(i+32)])

    def writeBuffer(self, buff):
        """
            Set the internal class buffer to buff
            buff: Array of bytes of length width*height
        """
        if len(self.BUFFER) == len(buff):
            self.BUFFER = buff

    def setDisplayON(self):
        """
            Turn display ON
        """
        self.writeCommand(self.DISPLAY_ON)

    def setDisplayOFF(self):
        """
            Turn display OFF
        """
        self.writeCommand(self.DISPLAY_OFF)

    def setDisplayINV(self, b=False):
        """
            Activate/Desactivate Inverse Mode
            b: True to activate Inverse Mode, False to desactivate
        """
        self.writeCommand(
            self.DISPLAY_INV_DISPLAY_OFF
            if b == False else
            self.DISPLAY_INV_DISPLAY_ON
        )

    def img2buffer(self, img):
        """
            Converte a monochrome image of WIDTH*HEIGHT size
            (used by PIL) to a buffer readable by the SSD1306
        """
        buffer = [0x0] * self.BUFFER_SIZE
        offset = [n*self.DISPLAY_WIDTH for n in range(0, 8)]
        for p in range(self.DISPLAY_PAGE_SIZE):
            start_page = p*self.DISPLAY_PAGE_LENGTH
            page_offset = p*self.DISPLAY_WIDTH
            for x in range(self.DISPLAY_WIDTH):
                buffer[page_offset+x] =  \
                    img[start_page + x] \
                    | img[start_page + offset[1] + x] << 1 \
                    | img[start_page + offset[2] + x] << 2 \
                    | img[start_page + offset[3] + x] << 3 \
                    | img[start_page + offset[4] + x] << 4 \
                    | img[start_page + offset[5] + x] << 5 \
                    | img[start_page + offset[6] + x] << 6 \
                    | img[start_page + offset[7] + x] << 7
        return buffer
