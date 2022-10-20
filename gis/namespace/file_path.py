"""
路径常量
"""
import platform

# win调试路径
outputPath = 'D:/同步空间/School/Codes/数据/DATA/'
binaryPath = outputPath + 'OLD_DIR/'
bdPath = outputPath + 'GIS.db'
programPath = "D:/同步空间/School/Codes/Python/DataProcess/2.0/"
# linux运行路径
if platform.system().lower() == 'linux':
    outputPath = '/home/DATA/'
    binaryPath = outputPath + 'OLD_DIR/'
    programPath = '/home/pi/gis/gis/'
    bdPath = programPath + 'GIS.db'
removePath = "/media/nvme"
configPath = programPath + 'config/'
