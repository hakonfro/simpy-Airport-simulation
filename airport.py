import simpy
import numpy as np
import matplotlib.pyplot as plt
import random

#Adjustable parameters
X_delay = 5 #expected delay for a flight in seconds
p_delay = 0.5 # expected value if a flight is delayed at all
plowtime = 60*10 #Time for a snowplow to clean the one landingstrip
numPlows = 5 #number of snowplows
numDeiceTrucks = 5 #Number of deiceing trucks
deiceTime = 60*10
coldWeather = True

#other constants:
t_guard = 60 #seconds
t_landing = 60
t_take_off = 60
X_turn_around = 45 * 60 #expected value
N_landingstrips = 2
infinity = 60*60*50

t_w1 = 60*60*1 #Expected value for snow = 1 hour
t_w2 = 60*60*2 # Expected value for nice weather = 2 hours
t_snow = 60*45 #Expected time for a runway to be filled with snow

SIM_TIME = 60*60*26

#Theata constants for the Erlang-distributions:
theta_delay = X_delay/3
theta_turn_around = X_turn_around/7

#These are only for plotting
inter_arrival_time_list = []
landingqueue = []
take_off_queue = []
turn_around_time_list = []
snowing_time = []
time = []

def turn_around():
    return np.random.gamma(7, theta_turn_around)

def isDelayed():
    rand = random.uniform(0,1)
    if (rand < p_delay):
        return 1
    else:
        return 0

def delay():
    return np.random.gamma(3,theta_delay)

def lmbd(t):
    minutes = t/60
    hours = minutes/60
    if hours > 5 and hours < 8:
        return 120
    elif hours > 8 and hours < 11:
        return 30
    elif hours > 11 and hours < 15:
        return 150
    elif hours > 15 and hours < 20:
        return 30
    elif hours > 20 and hours < 24:
        return 120
    else:
        return 0

def inter_arrival_time():
    time = env.now
    t = np.random.exponential(lmbd(env.now))
    return max(t_guard, t)

class Airport(object):
    """ An airport has limited number of runways. An airplane has to
    request landing and take off on one of the N landingstrips.
    Request are queued and landing request has higher priority than
    take off requests.
    """
    def __init__(self, env, num_landingstrips):
        self.env = env
        self.runway = simpy.PriorityResource(env, num_landingstrips)
        self.num_landingstrips = num_landingstrips
        self.snowplows = simpy.Resource(env, numPlows)
        self.plowingMachine = env.process(self.snowplow())
        self.deicetruckResource = simpy.Resource(env, numDeiceTrucks)
        

    def snowplow(self):
        while True:
            try:
                yield self.env.timeout(infinity)
            except simpy.Interrupt:
                print("Snowplow running at %.2f" % (self.env.now/60/60))
                yield self.env.timeout(plowtime)

    def deIceTruck(self):
        while True:
            try:
                yield self.env.timeout(infinity)
            except simpy.Interrupt:
                print("Deicetruck running at %.2f" % (self.env.now/60/60))

def plane(env, name, ap, delay):
    yield env.timeout(delay)
    time.append(env.now)
    print('%s arrives the airport at %.2f.' % (name, env.now/60/60))
    now = env.now
    with ap.runway.request(1) as request:
        yield request
        now = env.now - now
        landingqueue.append(now)
        print('%s enters the landingstrip at %.2f.' % (name, env.now/60/60))
        yield env.timeout(t_landing)
        print('%s leaves the runway at %.2f.' % (name, env.now/60/60))
    turn_around_plane=turn_around()
    turn_around_time_list.append(turn_around_plane)
    yield env.timeout(turn_around_plane)
    if(coldWeather):
        with ap.deicetruckResource.request() as request:
            yield request
            print('%s are being deiced at %.2f.' % (name, env.now/60/60))
            yield env.timeout(deiceTime)
    clock = env.now #for research purposes
    with ap.runway.request(2) as request:
        yield request
        take_off_queue.append((env.now - clock))
        print('%s enters the landingstrip for take-off at %.2f.' % (name, env.now/60/60))
        #yield env.process(ap.take_off(name))
        yield env.timeout(t_take_off)
        print("%s toke off at %.2f. Runway free..." % (name, env.now/60/60))
class Weather(object):
    """ Each time snow occurs. The weather class issue n=runways snowing processes.
    Each snowing process will capture its own runway if its filled with snow, making no planes able to use it.
    Each snowing process will also request a snowplow. When plowing its done, the runway is useable again.
    When snowing stops, the Weather class will then interrupt each snowing process, making also the runway useable for planes.
    """
    def __init__(self, env, airport):
        self.env = env
        self.airport = airport
        self.action = env.process(self.run())
        self.runways = []

    def run(self):
        while True:
            yield env.timeout(np.random.exponential(t_w2))
            print("It started to snow at", env.now/60/60)
            startsnowingtime = env.now #for plot
            intensity = np.random.exponential(t_snow)
            print("intensity:", intensity)
            for i in range (airport.num_landingstrips):
                self.runways.append(env.process(snowing(env, i ,airport, intensity)))
            yield env.timeout(np.random.exponential(t_w1))
            print("It stop snowing at", env.now/60/60)
            snowing_time.append((startsnowingtime, env.now))
            for p in self.runways:
                p.interrupt()
            self.runways.clear()


def snowing(env, runwayNum, ap, intensity):
    """ Snow process: This process will fill one runway with snow """
    snowing = True
    while snowing:
        try:
            yield env.timeout(intensity)
            with ap.runway.request(0) as request:
                yield request
                print("Runway %d needs plowing!!! at %.2f" % (runwayNum, env.now/60/60))
                tt = env.now
                with ap.snowplows.request() as req:
                    yield req
                    print(runwayNum ,"snowplow accessed" ,env.now - tt, "for", plowtime)
                    yield env.timeout(plowtime)
                    #ap.plowingMachine.interrupt()
        except simpy.Interrupt:
            snowing = False

def generator(env, airport):
    '''Generate planes arrivals at the airport according to the assignment'''
    yield env.timeout(60*60*5)
    i = 1
    while env.now < 86400:
        planedelay = 0
        inter_arrival = inter_arrival_time()
        planedelay = isDelayed() * delay()
        if (planedelay != 0):
            print('Airplane %d is delayed with %.2f' % (i, planedelay))
        env.process(plane(env, 'Airplane: %d' % i, airport, planedelay))
        i = i + 1
        inter_arrival_time_list.append((planedelay+inter_arrival))
        yield env.timeout(inter_arrival)

def print_stats(res):
    """For Debug purposes"""
    print('\n---------')
    print(f'{res.count} of {res.capacity} slots are allocated.')
    print(f' Users: {res.users}')
    print(f' Queued events: {res.queue}')
    print('-----------')

def plot_interarrival_time():
    '''Assignment a) Plotting interarrival times'''
    for i in range( len(time)):
        time[i] = time[i]/3600
    
    plt.xlabel("Time of the day")
    plt.ylabel('Time in seconds')
    plt.plot(time, inter_arrival_time_list, label = 'Interarrival time')
    plt.legend()
    plt.show()

def plot():
    '''Function for plotting the simulation'''
    for i in range (len(time)):
        time[i] = time[i]/3600

    new_snowing_time = []
    for i in range (len(snowing_time)):
        tmp = snowing_time[i][0]
        tmp = tmp/3600
        tmp2 = snowing_time[i][1]
        tmp2 = tmp2/3600
        new_snowing_time.append((tmp,tmp2))

    for i in range(len(take_off_queue), len(time)):
        take_off_queue.append(0)

    plt.xlabel("Time of the day")
    plt.ylabel('Time in seconds')
    plt.plot(time,landingqueue, label = 'Landing queue')
    plt.plot(time, take_off_queue, label = 'Take-off queue')

    #marking snow in plot
    for i in range (len(new_snowing_time)):
        plt.axvspan(new_snowing_time[i][0], new_snowing_time[i][1], facecolor = '0.5', alpha = 0.5)

    plt.legend()
    plt.show()

#Executing the simulation:
env = simpy.Environment()
airport = Airport(env, N_landingstrips)
if (coldWeather):
    weater = Weather(env, airport)

env.process(generator(env, airport))
env.run(until=SIM_TIME)

#plot_interarrival_time()
plot()
