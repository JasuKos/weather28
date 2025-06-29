from machine import WDT
wdt = WDT(timeout=75000)

import machine
machine.freq(240000000)
del machine
gc.collect()
print("Muistia alussa: "+str(gc.mem_free()))

import time
from machine import Pin, SPI, PWM
pwm = PWM(Pin(21), freq=200, duty=29)

# Alustetaan WiFi
import network
import config
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print('connecting to network...')
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    while not wlan.isconnected():
        pass
print('network config:', wlan.ifconfig())

# Display 
from ili9341 import Display, color565
spi = SPI(1, baudrate=40000000, sck=Pin(14), mosi=Pin(13))
display = Display(spi, dc=Pin(2), cs=Pin(15), rst=Pin(12))

def weather():
    import urequests2 as urequests
    gc.collect()
    print("Muistia vapaana: "+str(gc.mem_free()))
    temps = urequests.request('GET', config.REQUESTURL)
    del urequests
    gc.collect()
    temps = list(((((temps).text.split("<gml:doubleOrNilReasonTupleList>",1)[1]).split("</gml:doubleOrNilReasonTupleList>",1)[0]).replace(" ","")).split("\n"))
    temps.pop(0)
    temps.pop()
    global temperatures
    temperatures = [float(i) for i in temps]
    gc.collect()

# Variables
kerta = 5
tu = 0

def getnettime():
    import ntptime
    ntptime.host='fi.pool.ntp.org'
    ntptime.settime()
    del ntptime
    gc.collect

def get_last_sunday(year, month):
    # Selvitetään kuukauden viimeinen päivä
    if month == 12:
        next_month = (year + 1, 1)
    else:
        next_month = (year, month + 1)

    # Haetaan seuraavan kuukauden ensimmäisen päivän aikaleima
    last_day = time.mktime((next_month[0], next_month[1], 1, 0, 0, 0, 0, 0)) - 86400  # Edellisen päivän aikaleima
    last_sunday = time.localtime(last_day)

    # Etsitään viimeinen sunnuntai
    while last_sunday[6] != 6:  # Indeksi 6 on viikonpäivä (sunnuntai)
        last_day -= 86400  # Vähennetään yksi päivä
        last_sunday = time.localtime(last_day)

    return last_sunday[:3]  # Palautetaan (vuosi, kuukausi, päivä) -tuple

def is_daylight_saving_time(year, month, day, hour):
    # Haetaan maaliskuun ja lokakuun viimeisen sunnuntain päivämäärä
    last_sunday_march = get_last_sunday(year, 3)[2]  # Otetaan päivä (kolmas elementti)
    last_sunday_october = get_last_sunday(year, 10)[2]

    # Kesäaika: maaliskuun viimeinen sunnuntai klo 03:00 UTC eteenpäin
    # Talviaika: lokakuun viimeinen sunnuntai klo 03:00 UTC eteenpäin
    if (month > 3 or (month == 3 and day > last_sunday_march)) and \
       (month < 10 or (month == 10 and day < last_sunday_october)):
        return True
    # Jos ollaan siirtymäpäivässä ja aika on 03:00 UTC tai myöhemmin, on kesäaika
    if month == 3 and day == last_sunday_march and hour >= 3:
        return True
    # Jos ollaan lokakuun siirtymäpäivässä ja aika on 03:00 UTC tai myöhemmin, on talviaika
    if month == 10 and day == last_sunday_october and hour >= 3:
        return False

    return False

# Aikakäsittely ja kesäajan/talviajan logiikka
def localclock():
    global tu, pvm, klo, viikonpaiva
    
    # Hakee nykyisen UTC-aikaleiman ja muuntaa sen paikalliseksi ajaksi
    aika_utc = time.localtime(time.time())  # UTC aika
    vuosi = aika_utc[0]  # tm_year on ensimmäinen elementti
    pv = aika_utc[2]  # tm_mday on kolmas elementti
    kk = aika_utc[1]  # tm_mon on toinen elementti
    tu = aika_utc[3]  # tm_hour on neljäs elementti
    mi = aika_utc[4]  # tm_min on viides elementti
    vkp = aika_utc[6]  # tm_wday on kuudes elementti: Viikonpäivä 0 = Maanantai, 6 = Sunnuntai
    
    # Tarkistetaan, onko kesäaika
    if is_daylight_saving_time(vuosi, kk, pv, tu):
        # Kesäaika: Lisää 3 tuntia aikaan (UTC +3)
        aika_local = time.localtime(time.time() + 3600 * 3 + 4)  # Lisää kolme tuntia kesäajan vuoksi
    else:
        # Talviaika: Suomen aika on UTC +2
        aika_local = time.localtime(time.time() + 3600 * 2 + 4)  # Lisää kaksi tuntia talviaikana
    
    # Päivämäärän ja kellonaajan laskeminen
    vuosi = aika_local[0]
    pv = aika_local[2]
    kk = aika_local[1]
    tu = aika_local[3]
    mi = aika_local[4]
    vkp = aika_local[6]
    
    # Muotoillaan minuutit
    if mi < 10:
        mi = "0" + str(mi)
    else:
        mi = str(mi)
    
    # Päivämäärä ja kellonaika
    pvm = f"{pv}.{kk}.{vuosi}"
    klo = f"{tu}:{mi}"

    # Viikonpäivän määrittäminen
    viikonpaiva_lista = ["MAANANTAI", "TIISTAI", "KESKIVIIKKO", "TORSTAI", "PERJANTAI", "LAUANTAI", "SUNNUNTAI"]
    viikonpaiva = viikonpaiva_lista[vkp]
    
def updatescr():
    global tu
    print(tu)
    if 7 <= tu <= 22:
        pwm.init(freq=200, duty=512) # 0-1023 päivä #255
    else:
        pwm.init(freq=200, duty=29) # 0-1023 yö #24
    pvmpaikka = int((239-acumin.measure_text(pvm))/2)
    klopaikka = int((239-acumin.measure_text(klo))/2)
    ulko = str(temperatures[0])+"="
    ulkopaikka = int((239-acumin.measure_text(str(temperatures[0])+"="))/2)
    # Display 5,59,113,167,221,275
    # Colors
    black = color565(0, 0, 0)
    lightgray = color565(255, 255, 255)
    mediumgray = color565(130,130,130)
    scale = color565(50,50,50)
    lagoon = color565(150, 255, 255)
    yellow = color565(255, 255, 170)
    blue = color565(100,100,255)
    red = color565(255,100,100)
    green = color565(100,255,100)
    gc.collect()
    #display.clear(black)
    print("yläpeitto")
    display.fill_rectangle(0,0,239,100,0)
    display.draw_text8x8((239 - len(viikonpaiva) * 8) // 2, 2, viikonpaiva, lightgray)
    display.draw_text(pvmpaikka, 17, pvm, acumin, lightgray)
    display.draw_text(klopaikka, 60, klo, acumin, lightgray)
    display.fill_rectangle(0,160,239,159,0)
    display.draw_text(ulkopaikka, 160, ulko, acumin, lagoon)
    x=10
    y=268+int(float(min(temperatures)))
    t=0
    xg=10
    maxtemp=0
    mintemp=0
    print("alapeitto")
    #display.draw_text8x8(x, (-20+y-2*int(temperatures[0])), str(temperatures[0]), lightgray, background=0)
    asteikko = tu + 1
    display.draw_line(10,y,230,y,mediumgray)
    display.draw_line(10,y-20,230,y-20,scale)
    display.draw_line(10,y+20,230,y+20,scale)
    display.draw_line(10,y+40,230,y+40,scale)
    display.draw_line(10,y-40,230,y-40,scale)
    while xg < 230:
        display.draw_line(xg,310,xg,218,scale)
        if asteikko > 9:
            display.draw_text8x8(xg-7, 308, str(asteikko), lightgray)
        else:
            display.draw_text8x8(xg-3, 308, str(asteikko), lightgray)
        asteikko = asteikko + 6
        if asteikko > 23:
            asteikko = asteikko - 24
        xg=xg+4*6
    
    display.draw_circle(x+2, y-int(2*float(temperatures[0])), 4, lagoon)
    while t <= (len(temperatures)-1):
        if t < (len(temperatures)-1):
            display.draw_line(x, y-int(2*float(temperatures[t])), x+4, y-int(2*float(temperatures[t+1])), green)
        if (temperatures[t] == max(temperatures)) and maxtemp==0:
            display.draw_text8x8(x, (-20+y-int(2*temperatures[t])), str(temperatures[t]), red, background=0)
            display.draw_circle(x+2, y-int(2*float(temperatures[t])), 4, red)
            maxtemp=1
        elif (temperatures[t] == min(temperatures)) and mintemp==0:
            display.draw_text8x8(x, (10+y-int(2*temperatures[t])), str(temperatures[t]), blue, background=0)
            display.draw_circle(x+2, y-int(2*float(temperatures[t])), 4, blue)
            mintemp=1
        x=x+4
        t=t+1
    gc.collect()

def wirelesstemp():
    # Ruuvi Tag
    from ruuvitag import RuuviTag

    # Ruuvi callback
    def cb(ruuvitag):
        # payload='Temperature,Sensor={0} Celsius={1}\nHumidity,Sensor={0} RH={2}\nPressure,Sensor={0} mBar={3}\nMovement,Sensor={0} count={4}\nRSSI,Sensor={0} dBm={5}\nBattery,Sensor={0} Volts={6}'.format(ruuvitag.mac.decode(), ruuvitag.temperature, ruuvitag.humidity, ruuvitag.pressure/100, ruuvitag.movement_counter, ruuvitag.rssi, ruuvitag.battery_voltage)
        # print(payload)
        # print(ruuvitag.temperature)
        ruuvitemp = str(round(ruuvitag.temperature, 1))+"="
        print("keskipeitto")
        display.fill_rectangle(0,100,219,60,0)
        display.draw_text(int((240-acumin.measure_text(ruuvitemp))/2), 118, ruuvitemp, acumin, 65516)

    # Ruuvi settings
    from config import whitelist
    ruuvi = RuuviTag(whitelist)
    ruuvi._callback_handler = cb
    ruuvi.scan()
    time.sleep(10)
    ruuvi._ble.active(False)
    del whitelist
    del ruuvi
    del RuuviTag
    gc.collect()

def fontsinit():
    # Fonts
    from xglcd_font import XglcdFont
    gc.collect()
    print('Loading Acumin Pro font')
    global acumin
    acumin = XglcdFont('fonts/acusaaiso.c', 28, 41, 45, 63)
    del XglcdFont
    gc.collect()

while True:
    kerta = kerta +1
    if kerta >= 5:
        weather() #temperatures
        getnettime() #set clock
        kerta=0
    gc.collect()
    localclock() #parse time
    gc.collect()
    fontsinit() #create font object
    updatescr() #update base view
    gc.collect()
    wirelesstemp() # update ruuvi temperature data to screen
    gc.collect()
    hetki = klo
    while (klo == hetki):
        localclock()
        # print(klo)
        time.sleep(2)
    #delete globals:
    del acumin
    #del temperatures
    gc.collect()
    print("Muistia lopussa: "+str(gc.mem_free()))
    wdt.feed()
