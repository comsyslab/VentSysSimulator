 #https://simpy.readthedocs.org/en/latest/simpy_intro/

# Imports
import simpy
import os
import math
import sys
import csv
import random
import datetime
import ast
import numpy

# Constants
Ts = 60
PRINT = False
LOG = False
IMPORT = False
if LOG:
    log = open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'stdout.log'), 'w')
T_FIN = 6*3600-60
G = []
f = open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'IndoorCo2Gen24h.csv'), 'r')
for line in f.readlines():
    G.append(float(line.replace('\n', '')))
f.close()

# Buildings parameters for automatic generation of building stock
NUM_BUILDINGS = (21+765+31)/2
N_MIN_AP_BG = 50 # Minimum number of apartments per building
N_MAX_AP_BG = 150 # Maximum number of apartments per building
N_BEHAV_SIM_LOADS = 1000 # Maximum number of BehavSim loads
VOL_MIN = 7500.0 # Minimum volume in building to calculate CO2 in m3
VOL_MAX = 15000.0 # Maximum volume in building to calculate CO2 in  m3

VOL_GDL = 10110.8 # Reference building volume in m3
PWR_REF_SUP_GDL = 700.0 # Power reference supply fan in reference building in W
PWR_REF_EXH_GDL = 1300.0 # Power  reference exhaust fan in reference building in W
Q_REF_GDL = 25000.0/3600 # Airflow reference reference building in m3/s

N_PWR_SUP_MIN = 1.0 # Minimum power exponent supply fan
N_PWR_SUP_MAX = 1.4 # Maximum power exponent supply fan
N_PWR_EXH_MIN = 0.8 # Minimum power exponent exhaust fan
N_PWR_EXH_MAX = 1.2 # Maximum power exponent exhaust fan
N_AIR_SUP_MIN = 0.4 # Minimum airflow exponent supply fan
N_AIR_SUP_MAX = 0.7 # Maximum airflow exponent supply fan
N_AIR_EXH_MIN = 0.4 # Minimum airflow exponent exhaust fan
N_AIR_EXH_MAX = 0.7 # Maximum airflow exponent exhaust fan
Q_MIN = Q_REF_GDL*0.2 # Minimum airflow reference building

# Global variables
global static_pressure
static_pressure = 0.25
global total_power
global sum_co2

all_time = []
total_power = []
sum_co2 = []
i = 0
while i < T_FIN:
    all_time.append(i)
    total_power.append(0)
    sum_co2.append(0)
    i += Ts

class DemandResponseController(object):
    def __init__(self, env, f_name, f_path=os.path.dirname(os.path.abspath('__file__'))):
        self.f_name = f_name
        self.f_path = f_path
        self.abs_file = os.path.join(self.f_path, self.f_name)

        self.default_pressure = static_pressure

        self.data = self.read_csv()

        self.env = env
        self.action = env.process(self.run())

    def read_csv(self):
        try:
            csv_data = []
            with open(self.abs_file, 'rb') as csvfile:
                reader = csv.reader(csvfile, delimiter=';', quotechar='|')
                next(reader, None)  # skip the headers

                for row in reader:
                    t_from = int(row[0])
                    t_to = int(row[1])
                    value = float(row[2])
                    row_int = [t_from, t_to, value] # time from, time to, static pressure
                    csv_data.append(row_int)
                return csv_data
        except:
            print "Unexpected error:", sys.exc_info()

    def run(self):
        global static_pressure
        t_fin = 0
        for row in self.data:
            t_ini = row[0]
            if (t_ini - t_fin) > 1:
                static_pressure = self.default_pressure
                if PRINT:
                    print "DR Provider: At %s I change static pressure to default %s" % (self.env.now, str(static_pressure))
                if LOG:
                    log.write("DR Provider: At %s I change static pressure to default %s" % (self.env.now, str(static_pressure)))
                yield self.env.timeout((t_ini - t_fin))
            else:
                pass
            t_fin = row[1]
            t_wait = row[1]-row[0]
            value = row[2]
            static_pressure = value
            if PRINT:
                print "DR Provider: At %s I change static pressure to %s" % (self.env.now, str(static_pressure))
            if LOG:
                log.write("DR Provider: At %s I change static pressure to %s" % (self.env.now, str(static_pressure)))
            yield self.env.timeout(t_wait)
        static_pressure = self.default_pressure
        if PRINT:
            print "DR Provider: At %s I change static pressure to default %s" % (self.env.now, str(static_pressure))
        if LOG:
            log.write("DR Provider: At %s I change static pressure to default %s" % (self.env.now, str(static_pressure)))

class IndoorCO2Level(object):
    def __init__(self, v=10110.8, q=25000/3600.0, c_out=400, g=1500, ts=60, c_ini=400):
        self.v = v              # Volume of building in m3 (apartments and common areas)
        self.q = q              # Airflow in m3/s
        self.c_out = c_out      # Outdoor CO2 in ppm
        self.g = g              # CO2 generation cm3/s
        self.ts = ts            # Sampling time in seconds
        self.c_ini = c_ini      # Initial CO2 concentration in ppm

    def co2_equation(self):
        try:
            Cfin = (self.q*(self.c_out-self.c_ini)+self.g)*self.ts/self.v+self.c_ini
            self.c_ini = Cfin
            return Cfin
        except:
            print "Unexpected error:", sys.exc_info()[0]

    def co2_model(self, t_fin, g=1500, q=25000/3600.0):
        self.g = g
        self.q = q
        try:
            t_now = 0
            out_time = [t_now]
            out_ppm = [self.c_ini]
            while t_now <= t_fin:
                c_1 = self.co2_equation()
                t_now += self.ts
                out_time.append(t_now)
                out_ppm.append(c_1)
            return out_time, out_ppm
        except:
            print "Unexpected error:", sys.exc_info()[0]

class VentilationSystem(object):
    """
    Ventilation system class is composed by two fans: supply and exhaust. The models of each fan is based in the
    affinity laws with non ideal exponents. The initialization parameters of this class are:
    :param ps_ref_sup: Reference relative static pressure for supply fan [0,1]
    :param ps_ref_exh: Reference relative static pressure for exhaust fan [0,1]
    :param q_ref_sup: Reference airflow for supply fan in m3/s
    :param q_ref_exh: Reference airflow for exhaust fan in m3/s
    :param pwr_ref_sup: Reference power for supply fan in W
    :param pwr_ref_exh: Reference power for exhaust fan in W
    :param n_pwr_sup: Affinity law power exponent for supply fan (idea 1.5)
    :param n_pwr_exh: Affinity law power exponent for exhaust fan (idea 1.5)
    :param n_air_sup: Affinity law airflow exponent for supply fan (idea 0.5)
    :param n_air_exh: Affinity law airflow exponent for exhaust fan (idea 0.5)
    """

    def __init__(self, ps_ref_sup, ps_ref_exh, q_ref_sup, q_ref_exh, pwr_ref_sup, pwr_ref_exh, n_pwr_sup, n_pwr_exh,
                 n_air_sup, n_air_exh, q_min):
        self.ps_ref_sup = ps_ref_sup
        self.ps_ref_exh = ps_ref_exh
        self.q_ref_sup = q_ref_sup
        self.q_ref_exh = q_ref_exh
        self.pwr_ref_sup = pwr_ref_sup
        self.pwr_ref_exh = pwr_ref_exh
        self.n_pwr_sup = n_pwr_sup
        self.n_pwr_exh = n_pwr_exh
        self.n_air_sup = n_air_sup
        self.n_air_exh = n_air_exh
        self.q_min = q_min

    def supply_fan(self, ps):
        # the  power consumption (W) of e
        try:
            pwr_sup = (math.pow(float(ps) / self.ps_ref_sup, self.n_pwr_sup) * self.pwr_ref_sup)
            # calculates the airflow m3/s from a given set point pressure
            q_sup = (math.pow(float(ps) / self.ps_ref_sup, self.n_air_sup)) * self.q_ref_sup
            if q_sup == 0.0:
                q_sup = self.q_min
            return pwr_sup, q_sup
        except:
            print "Unexpected error:", sys.exc_info()[0]

    def exhaust_fan(self, ps):
        try:
            pwr_exh = (math.pow((float(ps)+6/303.0) / self.ps_ref_exh, self.n_pwr_exh) * self.pwr_ref_exh)
            q_exh = (math.pow((float(ps)+6/303.0) / self.ps_ref_exh, self.n_air_exh) * self.q_ref_exh)
            return pwr_exh, q_exh
        except:
            print "Unexpected error:", sys.exc_info()[0]

    def next_values(self, ps=80/303.0):
        exhaust_fan = self.exhaust_fan(ps)
        supply_fan = self.supply_fan(ps)
        pwr_sys = exhaust_fan[0]+supply_fan[0]
        q_sys = supply_fan[1]
        return pwr_sys, q_sys

class Household(object):
    """
    This class contains the load profile of a household. On initialization it reads a load profile from a CSV
    file generated by BehavSim and introduces it into a list. The method next_load() returns the current
    load.
    :param f_name: File name with the household load profile
    :param f_path: Absolute path with the file
    """

    def __init__(self, f_name='load.csv', f_path=os.path.dirname(os.path.abspath('__file__'))):
        self.f_name = f_name
        self.f_path = f_path
        t, val = csv2array(f_name=self.f_name, f_path=self.f_path, headline=True)
        self.index = 0
        self.load = val

    def next_load(self):
        if self.index < len(self.load):
            val = self.load[self.index]
            self.index += 1
        else:
            val = 'NaN'
        return val

class Building(object):
    def __init__(self, env, b_id=1, n_apartments=2, vol=10110.8, ps_ref_sup=80/303.0, ps_ref_exh=86/303.0,
                 q_ref_sup=25000.0/3600, q_ref_exh=25000.0/3600, pwr_ref_sup=700.0, pwr_ref_exh=1300.0,
                 n_pwr_sup=1.19, n_pwr_exh=0.92, n_air_sup=0.67, n_air_exh=0.50, q_min=Q_MIN, g=G, f_names=['load.csv', 'load.csv'],
                 f_path=os.path.dirname(os.path.abspath('__file__'))):

        self.env = env

        self.b_id = b_id
        self.n_apartments = n_apartments

        self.vol = vol
        self.ps_ref_sup = ps_ref_sup
        self.ps_ref_exh = ps_ref_exh
        self.q_ref_sup = q_ref_sup
        self.q_ref_exh = q_ref_exh
        self.pwr_ref_sup = pwr_ref_sup
        self.pwr_ref_exh = pwr_ref_exh
        self.n_pwr_sup = n_pwr_sup
        self.n_pwr_exh = n_pwr_exh
        self.n_air_sup = n_air_sup
        self.n_air_exh = n_air_exh
        self.g = g
        self.q_min = q_min

        self.f_names = f_names
        self.f_path = f_path

        self.all_apartments = []

        self.action = self.env.process(self.run())

    def run(self):
        global total_power
        global sum_co2
        vent_sys = VentilationSystem(self.ps_ref_sup, self.ps_ref_exh, self.q_ref_sup, self.q_ref_exh, self.pwr_ref_sup,
                                     self.pwr_ref_exh, self.n_pwr_sup, self.n_pwr_exh, self.n_air_sup, self.n_pwr_exh,
                                     q_min=self.q_min)

        co2 = IndoorCO2Level(v=self.vol, ts=Ts)
        i = 0
        while i < self.n_apartments:
            aux = Household(self.f_names[i], self.f_path)
            self.all_apartments.append(aux)
            i += 1
        while True:
            yield self.env.timeout(Ts)
            # Run Ventilation System
            pwr_vent, q_vent = vent_sys.next_values(static_pressure)
            if PRINT:
                print "Building %s: At %s with static pressure %s power %s W and airflow %s " \
                  "m3/s" %(str(self.b_id), self.env.now, str(static_pressure), str(pwr_vent), str(q_vent))
            if LOG:
                log.write("Building %s: At %s with static pressure %s power %s W and airflow %s " \
                  "m3/s" %(str(self.b_id), self.env.now, str(static_pressure), str(pwr_vent), str(q_vent)))

            # Indoor CO2 Model
            # aux_indx = self.env.now/3600
            g_aux = numpy.interp(self.env.now, range(0, 3600*24, 3600), G) # change this depending on G time resolution
            # g_aux = self.g[aux_indx]
            co2.co2_model(t_fin=Ts, q=q_vent, g=g_aux)
            if PRINT:
                print "Building %s: At %s with airflow %s m3/s has CO2 level of %s " \
                  "ppm" %(str(self.b_id), self.env.now, str(q_vent), str(co2.c_ini))
            if LOG:
                log.write("Building %s: At %s with airflow %s m3/s has CO2 level of %s " \
                  "ppm" %(str(self.b_id), self.env.now, str(q_vent), str(co2.c_ini)))

            sum_co2[self.env.now/60-1] += co2.c_ini

            # Households load
            sum = 0
            for apartment in self.all_apartments:
                sum += apartment.next_load()
            if PRINT:
                print "Building %s: At %s has consumption of %s W in all" \
                      " apartments" % (str(self.b_id), self.env.now, str(sum))
            if LOG:
                log.write("Building %s: At %s has consumption of %s W in all" \
                      " apartments" % (str(self.b_id), self.env.now, str(sum)))

            # Update Total Power
            total_power[self.env.now/60-1] += sum+pwr_vent

def gen_fake_behavsim_load(t_fin=3600, f_name='load.csv'):
    t_now = 0
    f = open(f_name, 'w')
    while t_now < t_fin:
        val = random.normalvariate(4000.0, 2000.0)
        if val < 0.0:
            val = 0.0
        line = "%s;%s\n" % (str(t_now), str(val))
        f.write(line)
        t_now += Ts
    f.close()

def csv2array(f_name, f_path=os.path.dirname(os.path.abspath('__file__')), headline=False, separator=';'):
    """
    This function is use to convert CSV to list.

    :param f_name: Name of the csv file to parse exmaple.csv
    :param f_path: Absolute path of the file to parse
    :param headline: True if first line contains description of file
    :param separator: Separator character
    :return: Returns 2 lists with same order
    """
    f_abs_path = os.path.join(f_path, f_name)
    f = open(f_abs_path, 'r')

    if headline:
        f.readline()
    else:
        pass
    output = []
    for variables in f.readline().replace('\n', '').split(separator):
        output.append([float(variables)])

    for line in f.readlines():
        i = 0
        for variables in line.replace('\n', '').split(separator):
            output[i].append(float(variables))
            i += 1
    f.close()

    return output

def create_csv(f_name='output.csv', f_path=os.path.dirname(os.path.abspath('__file__')), rows=[[1,2,3], [11,22,33]],
               labels=['col1', 'col2']):

    f_abs_path = os.path.join(f_path, f_name)
    f = open(f_abs_path, 'w')

    header = ''
    for label in labels:
        header += label + ';'
    f.write(header[:-1] +'\n')

    max_rows = len(rows[0])
    max_cols = len(rows)

    i = 0
    while i < max_rows:
        j = 0
        line = ''
        while j < max_cols:
            line += str(rows[j][i]) + ';'
            j += 1
        f.write(line[:-1]+'\n')
        i += 1
    f.close()

def import_simulator_config(f_name, id, f_path=os.path.dirname(os.path.abspath('__file__'))):
    f_abs_path = os.path.join(f_path, f_name)
    f = open(f_abs_path, 'r')
    f.readline()
    for line in f.readlines():
        b_id, n_ap, vol, q_ref_sup, q_ref_exh, pwr_ref_sup, pwr_ref_exh, n_pwr_sup, n_pwr_exh, n_air_sup, n_air_exh, q_min, g, f_names = line.replace('\n', '').split(';')
        if int(b_id) == id:
            return int(n_ap), float(vol), float(q_ref_sup), float(q_ref_exh), float(pwr_ref_sup), float(pwr_ref_exh), float(n_pwr_sup), float(n_pwr_exh), float(n_air_sup), float(n_air_exh), float(q_min), ast.literal_eval(g), ast.literal_eval(f_names)
        else:
            pass
    f.close()


if __name__ == "__main__":
    #gen_fake_behavsim_load(t_fin=T_FIN+60)
    t_start = datetime.datetime.now()
    print "Starting simulation at: %s" % str(t_start)

    env = simpy.Environment()

    # Define all buidlings
    i = 1
    if IMPORT:
        while i <= NUM_BUILDINGS:
            num_apartments, vol, q_ref_sup, q_ref_exh, pwr_ref_sup, pwr_ref_exh, n_pwr_sup, n_pwr_exh, n_air_sup, n_air_exh, q_min, G_building, f_names = import_simulator_config(f_name='SimulationConfiguration.csv', id=i)

            Building(env, b_id=i, n_apartments=num_apartments, vol=vol, q_ref_sup=q_ref_sup, q_ref_exh=q_ref_exh,
                     pwr_ref_sup=pwr_ref_sup, pwr_ref_exh=pwr_ref_exh, n_pwr_sup=n_pwr_sup, n_pwr_exh=n_pwr_exh,
                     n_air_sup=n_air_sup, n_air_exh=n_air_exh, q_min=q_min, g=G_building, f_names=f_names,
                     f_path=os.path.join(os.path.dirname(os.path.abspath('__file__')), 'aggregated-behavsim-loads'))

            i += 1
    else:
        f = open(os.path.join(os.path.dirname(os.path.abspath('__file__')), 'SimulationConfiguration.csv'), 'w')
        header = 'Building ID;Number Apartments [-];Building Volume [m3];Reference Airflow Supply Fan [m3/s]; ' \
              'Reference Airflow Exhaust Fan [m3/s];Reference Power Supply Fan [W];Reference Power Exhaust Fan [W];' \
              'Power Exponent Supply Fan [-];Power Exponent Exhaust Fan [-];Airflow Exponent Supply Fan [-];' \
              'Power Exponent Exhaust Fan [-]; Minimum Airflow [m3/s]; Indoor CO2 Generation G [cm3/s] ;' \
                 'List Used Files for Household Load\n'
        f.write(header)
        while i <= NUM_BUILDINGS:
            # Randomize the aparments
            num_apartments = random.randint(N_MIN_AP_BG, N_MAX_AP_BG)
            # Randomly select a list of file names from the BehavSim load generated
            f_names = []
            for j in range(0, num_apartments):
                aux_num = str(random.randint(1, N_BEHAV_SIM_LOADS))
                f_names.append('house_%s.csv' %aux_num.zfill(6))
            vol = random.uniform(VOL_MIN, VOL_MAX)
            q_ref_sup = vol/VOL_GDL*Q_REF_GDL
            q_ref_exh = vol/VOL_GDL*Q_REF_GDL
            pwr_ref_sup = vol/VOL_GDL*PWR_REF_SUP_GDL
            pwr_ref_exh = vol/VOL_GDL*PWR_REF_EXH_GDL
            n_pwr_sup = random.uniform(N_PWR_SUP_MIN, N_PWR_SUP_MAX)
            n_pwr_exh = random.uniform(N_PWR_EXH_MIN, N_PWR_EXH_MAX)
            n_air_sup = random.uniform(N_AIR_SUP_MIN, N_AIR_SUP_MAX)
            n_air_exh = random.uniform(N_AIR_EXH_MIN, N_AIR_EXH_MAX)
            q_min = vol/VOL_GDL*Q_MIN
            G_building = []
            for value in G:
                G_building.append(value*vol/VOL_GDL)

            txt = '%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%s\n' % (str(i), str(num_apartments), str(vol),str(q_ref_sup), str(q_ref_exh), str(pwr_ref_sup), str(pwr_ref_exh), str(n_pwr_sup), str(n_pwr_exh), str(n_air_sup), str(n_air_exh), str(q_min), str(G_building), str(f_names))
            f.write(txt)

            Building(env, b_id=i, n_apartments=num_apartments, vol=vol, q_ref_sup=q_ref_sup, q_ref_exh=q_ref_exh,
                     pwr_ref_sup=pwr_ref_sup, pwr_ref_exh=pwr_ref_exh, n_pwr_sup=n_pwr_sup, n_pwr_exh=n_pwr_exh,
                     n_air_sup=n_air_sup, n_air_exh=n_air_exh, q_min=q_min, g=G_building, f_names=f_names,
                     f_path=os.path.join(os.path.dirname(os.path.abspath('__file__')), 'aggregated-behavsim-loads'))
            i += 1
        f.close()

    # Define demand response controller
    DemandResponseController(env, "dr_controller_test.csv")

    env.run(until=T_FIN+1)
    t_fin = datetime.datetime.now()
    print "Finish simulation at: %s (elapsed %s)" % (str(t_fin), str(t_fin-t_start))

    # Format results
    avg_co2 = []
    for value in sum_co2:
        avg_co2.append(value/NUM_BUILDINGS)

    create_csv(rows=[all_time, total_power, avg_co2], labels=['Time [s]', 'Total Power [W]', 'CO2 Level [ppm]'])



