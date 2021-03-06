# try to use whole network as class that runs in environment

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
import heapq
import matplotlib.animation as animation
import time
from scipy.interpolate import interp1d
import math
from typing import List

from globals import *  # loading some variables and constants
from helpers import heap_delete


class Net(object):

    def __init__(self, n, p, p_i, max_t, seed, clustering_target = None):

        # TODO try and decrease complexity, this seems convoluted

        print("Initializing network...")
        start = time.time()

        np.random.seed(seed)
        # random.seed(seed)

        self.n = n
        self.p = p
        self.p_i = p_i
        self.clustering_target = clustering_target

        # self.graph = nx.gnp_random_graph(n, p, seed = seed)
        self.graph = nx.fast_gnp_random_graph(n, p, seed = seed)

        if p == 0:
            print('Warning: p = 0, so the graph will not be checked for connectedness.')
            self.graph = nx.fast_gnp_random_graph(n, p, seed = seed)
            self.last_seed = seed
        else:
            while not nx.is_connected(self.graph):
                # I only want connected graphs, otherwise i cannot really compare
                seed += 1
                self.graph = nx.fast_gnp_random_graph(n, p, seed = seed)
            # print(seed)
            else:
                self.last_seed = seed # this is the seed that was used.
                # I save this so I can choose a different one when I want to create a new net in mc

        if self.clustering_target:
            self.alter_clustering_coeff(clustering_target,clustering_epsilon)

        self.colormap = ['green' for i in range(n)]

        self.event_list = []
        heapq.heapify(self.event_list)

        self.max_t = max_t

        # I dont want to deal with a whole mutable state list, so I only save the current count at regular intervals:
        self.count = np.zeros([5,1], dtype=np.int32).flatten() # current state
        # susceptible, exposed, infectious, recovered, transmission_disabled are the 5 rows

        self.count[0] = n
        # TODO delete last row, this count is deprecated
        self.counts = np.zeros([5, math.floor(max_t/resolution)], dtype=np.int32) # history, gets written in sim()



        self.net_states = [] # this is a list of nets at equidistant time steps
        # i use this for the animation

        # for comparison, even new network structures use same layout (this only writes self.pos once, at start)
        try:
            a = self.pos # TODO this and the hard option of reset() is rather quick & dirty
        except AttributeError:
            self.pos = nx.spring_layout(self.graph, seed=seed)

        for id in range(n):
            # at first all are susceptible
            # print(net.nodes)
            # print(net.edges)
            self.graph.nodes[id]['state'] = 0

        nx.set_edge_attributes(self.graph, False, name = 'blocked')
        nx.set_node_attributes(self.graph, [], name = 'contacts')

        # TODO this is a little rough...
        #  essentially I want to set a reset point because some of the values are changed in place and I need a fresh
        #  start for each monte carlo. Resetting is done via the self.reset() function
        self.init_state = {}
        for key in self.__dict__.keys():
            try:
                self.init_state[key] = self.__dict__[key].copy()
            except AttributeError:
                # print(key)
                self.init_state[key] = self.__dict__[key]

        end = time.time()

        print("Network initialized. Time elapsed: {}s.".format(end - start))

        # self.draw()
    # events:

    def infection(self, time, id):

        self.update_state(id, 1)  # exposed now
        self.count += susc2exp
        self.colormap[id] = 'yellow'
        # print('Person #{} has been exposed at time {}'.format(id, time))

        # there is a possibility that one individual gets several infection events scheduled to by different people
        # for this i created a mode for the canceling edge that cancels all scheduled events:
        self.cancel_event(id, INFECTION, all=True)

        # schedule infectious event
        t_i_random = np.random.exponential(scale=t_i, size=1)[0]
        heapq.heappush(self.event_list, (time + t_i_random, INFECTIOUS, id))

    def infectious(self, time, id, mode):
        # print('Person #{} started being infectious at time {}'.format(id, time))
        self.update_state(id,2)
        self.count += exp2inf
        self.colormap[id] = 'red'

        t_c_random = np.random.exponential(scale=t_c, size=1)[0]
        t_r_random = np.random.exponential(scale=t_r, size=1)[0]



        heapq.heappush(self.event_list, (time + t_c_random,CONTACT, id))
        heapq.heappush(self.event_list, (time + t_r_random ,RECOVER, id))

        if mode == 'quarantine' or mode == 'tracing':
            t_q_random = np.random.exponential(scale=t_q, size=1)[0]
            heapq.heappush(self.event_list, (time + t_q_random ,QUARANTINE, id))


        if mode == 'tracing':
            heapq.heappush(self.event_list, (time + t_q_random ,TRACING, id))
            # I will simply do these two at the same time (when the infection is detected)
            # the tracing event adds a little bit of time for the process of finding and alerting contacts

    def contact(self, time, id):

        # friends = list(self.graph.neighbors(id))
        # connections = list(self.graph.edges)
        friends = list((friend for friend in self.graph.neighbors(id)
                        if self.graph.edges[id, friend]['blocked'] == False))
                # can only use edges that aren't blocked due to quarantine



        if friends:
            # contacted_friend = random.choice(friends)
            contacted_friend_idx = np.random.choice(len(friends),1)[0]
            contacted_friend = friends[contacted_friend_idx]
            self.graph.nodes[id]['contacts'].append(contacted_friend)
        else:
            t_c_random = np.random.exponential(scale=t_c, size=1)[0]
            next_contact = (time+t_c_random, CONTACT, id)
            heapq.heappush(self.event_list, next_contact)
            return

        # if self.graph.nodes[id]['state'] == 3:
        #     yield

        if self.graph.nodes[contacted_friend]['state'] == 0:

            # print('#' + str(id) + ' has had contact with #{}.'.format(contacted_friend))
            # u = random.uniform(0,1)
            u = np.random.uniform()

            if u < self.p_i:
                heapq.heappush(self.event_list, (time, INFECTION, contacted_friend))
        else:
            pass  # if in any other state than susceptible, this contact does not matter




        if self.graph.nodes[id]['state'] == 2:

            t_c_random = np.random.exponential(scale=t_c, size=1)[0]

            next_contact = (time+t_c_random, CONTACT, id)
            # if person is not infectious anymore, no need to schedule this
            heapq.heappush(self.event_list, next_contact)
        else:
            next_contact = False

        self.graph.nodes[id]['latest_contact'] = next_contact
        # this stores a pointer to the latest contact process of this id OR FALSE IF NONE IS SCHEDULED
        # it can be used to interrupt said process should the patient recover in the meantime

    def recover(self, time, id):
        # cancel related contact event

        try:
            if self.graph.nodes[id]['latest_contact']:
                self.cancel_event(id, CONTACT, all=False)
        except KeyError:
            pass
        # try:
        #     if self.graph.nodes[id]['latest_contact']:
        #         copy = self.event_list.copy()
        #
        #         # TODO this could be faster, i can use heap structure to stop earlier right?
        #         fitting_events = []
        #         for i, event in enumerate(copy):
        #             if event[0] == 2 and event[2] == id:
        #                 fitting_events.append((event[0], i))
        #                 # with time and index i have all information needed to cancel
        #                 # NEXT scheduled event with this id and type
        #         cancel_prioritized = sorted(fitting_events, key= lambda x: x[0]) # sort for time
        #         try:
        #             i = cancel_prioritized[0][1] # gets index of original heap
        #             heap_delete(self.event_list, i)
        #         except IndexError: # no scheduled event that fits
        #             pass
        # except:
        #     pass

        if self.graph.nodes[id]['state'] == NO_TRANS_STATE:
            self.count += no_trans2rec
        else:
            self.count += inf2rec

        self.update_state(id, 3)  # individuum is saved as recovered
        self.colormap[id] = 'grey'
        # print(str(id)+' has recovered.')

        # print('Contact process stopped due to recovery.')

    def quarantine(self, time, id):


        connections = list(((id,friend) for friend in self.graph.neighbors(id)))
        for id,friend in connections:
            self.graph.edges[id,friend]['blocked'] = True

        # in my simple model it would be possible for someone to be already recovered when the quarantine event happens
        # in this case, the color won't change to blue (because no contact event will ever happen anyways)
        if self.graph.nodes[id]['state'] == REC_STATE:
            pass
        else:
            # self.update_state(id, NO_TRANS_STATE)  # update state to transmission disabled
            # self.count += inf2no_trans
            self.colormap[id] = 'blue'


        heapq.heappush(self.event_list, (time + quarantine_time,END_OF_QUARANTINE, id))

    def end_of_quarantine(self, time, id):
        connections = list(((id,friend) for friend in self.graph.neighbors(id)))
        for id,friend in connections:
            if self.colormap[friend] != 'blue':
                # this should keep connections blocked if the other side is in quarantine
                self.graph.edges[id,friend]['blocked'] = False
            # TODO this (no if clause)
            #  leaves a weird possibility: if person a and b both are quarantined,
            #  the first one (say a) going out of quarantine would also re-enable the connection between
            #  the two, even if b is still quarantined. Should not change much, though.
            #  OK THIS DEFINITELY MATTERS. leaving the if clause out means more people get infected than
            #  without tracing...

    def tracing(self, time, id):
        contacts = self.graph.nodes[id]['contacts']
        for contact in contacts:
            t_t_random = np.random.exponential(scale=t_t, size=1)[0]
            heapq.heappush(self.event_list, (time + t_t_random ,QUARANTINE, id))
        contacts.clear()


    # simulation

    def sim(self, seed, mode = None):
        # call first infection event

        np.random.seed(seed)

        start = time.time()

        print('Simulation started.')

        event = (0, INFECTION, 0)  # ind. #0 is infected at t = 0
        heapq.heappush(self.event_list, event)

        # intervals = 1 # days for each animation frame
        counter = 0

        # end_of_sim = -1

        while self.event_list:

            event = heapq.heappop(self.event_list)

            current_t = event[0]

            if current_t > self.max_t:
                break

            # if it exceeds the current sampling point, the current counts are saved before doing the event (hold)
            if current_t >= counter * resolution:
                assert (
                                   self.count >= 0).all() and self.count.sum() == self.n, 'Something went wrong, impossible states detected.'

                self.counts[:, counter] = self.count
                self.net_states.append((0, self.colormap.copy()))
                counter += 1

            self.do_event(event, mode)

        end_of_sim = current_t  # this is where the simulation stopped. After that, states remain constant
        for i in np.arange(start=counter, stop=self.counts.shape[1], dtype=int):
            self.counts[:, i] = self.counts[:, i - 1]  # otherwise it is all 0 at some point

        end = time.time()

        print('Simulation complete. Simulation time : {}s.'.format(end - start))

        # self.plot_timeseries()
        return self.counts

    def do_event(self, event, mode):
        time = event[0]
        type = event[1]  # REARRANGED as (time, type, id) because heapq sorts only for first...
        # TODO check whether i changed it everywhere...
        id = event[2]
        # events:
        # 0:infection
        # 1:infectious
        # 2:contact
        # 3:recovery

        if type == 0:
            self.infection(time, id)
        elif type == 1:
            self.infectious(time, id, mode)
        elif type == 2:
            self.contact(time, id)
        elif type == 3:
            self.recover(time, id)
        elif type == QUARANTINE:
            self.quarantine(time, id)
        elif type == END_OF_QUARANTINE:
            self.end_of_quarantine(time,id)
        elif type == TRACING:
            self.tracing(time, id)
        else:
            raise Exception('This event type has not been implemented')

    def cancel_event(self, id, event_id, all=False):
        # the "all" parameter is here because for now I assume that all infection events must be canceled once
        #  the infection has commenced TODO review
        #  (so for an infected individual no other infection events shall occur
        copy = self.event_list.copy()

        fitting_events = []
        for i, event in enumerate(copy):
            if event[0] == event_id and event[2] == id:
                fitting_events.append((event[0], i))
                # with time and index i have all information needed to cancel
                # NEXT scheduled event with this id and type

        if all:  # want to delete all events of that type for that individual
            indices = [i for bin, i in fitting_events]  # i want these gone
            # https://stackoverflow.com/a/32744088 for using numpy to delete certain entries:
            # copy = np.delete(copy, indices).tolist()

            # now i want to delete the entries that need to be canceled from the list:
            indices.reverse()
            # traverse backwards because deleting the i-th entry would change the following indices
            # NOTE: originally, they are ascending because of enumerate

            for i in indices:
                idx = indices[-i - 1]
                heap_delete(self.event_list, idx)
                # TODO this might actually be worse than just using del here and heapify in the end
                #  I think this would be both O(n)?

            # this is O(n) and by using siftdown and siftup each time i delete an entry i could make it faster, O(logn)
            # however, I have to traverse the whole list anyways at the start so it will always be O(n)...
            # heapq.heapify(copy)
            # self.event_list = copy
            return

        else:  # # want to delete just next event of that type for that individual
            # TODO this is not efficient
            cancel_prioritized = sorted(fitting_events, key=lambda x: x[0])  # sort for time
            try:
                i = cancel_prioritized[0][1]  # gets index of original heap
                heap_delete(self.event_list, i)
            except IndexError:  # no scheduled event that fits
                pass

    def monte_carlo(self, n, mode = None):
        # net is input
        # run sim n times, saving the output in list
        results: List[np.ndarray] = []
        for i in range(n):
            redo = not bool((i + 1)%redo_net) # redo_net is in globals.py, every i iterations net is changed as well
            self.reset(hard = redo)
            if redo:
                print(self.clustering())
            results.append(self.sim(seed=i, mode = mode).copy())


        # compute mean
        mean = np.zeros(results[0].shape)
        for counts in results:
            mean += counts
        mean /= len(results)

        return mean

    def reset(self, hard = False):
        # see note in __init__. Short: reset to original state (deepcopy), OR redo whole network
        # TODO unsafe?
        if hard:
            self.__init__(self.n, self.p, self.p_i, self.max_t, self.last_seed + 1, clustering_target=self.clustering_target)
            # this overwrites the network with a new one of different seed (as opposed to just jumping to save point)
        else:
            for key in self.init_state.keys():
                if key != 'init_state':
                    try:
                        self.__dict__[key] = self.init_state[key].copy()
                    except AttributeError:
                        # print(key)
                        self.__dict__[key] = self.init_state[key]


    # visuals

    def plot_timeseries(self, counts=None, save = None):
        print('Plotting time series...')

        plt.clf()

        n_counts = self.counts.shape[1]
        ts = np.arange(start=0, stop=self.max_t, step=resolution)

        # TODO this is not optimal... I would like the vertical lines to disappear
        # from https://docs.scipy.org/doc/scipy/reference/tutorial/interpolate.html
        # x = np.linspace(0, 10, num=11, endpoint=True)
        x = ts

        # by default, i use the classes last simulation results.
        # but for monte carlo i want to be able to plot something manually as well
        if isinstance(counts, np.ndarray):
            y = counts.T
        else:
            y = self.counts.T  # in case counts is not given, take the ones saved from last simulation

        # f1 = interp1d(x, y, kind='nearest')
        f2 = interp1d(x, y, kind='previous', axis=0)
        # f3 = interp1d(x, y, kind='next')
        xnew = np.linspace(0, self.max_t - resolution, num=10001, endpoint=False)
        # plt.plot(x, y, 'o')
        plt.plot(xnew, f2(xnew))
        # plt.legend(['data', 'nearest', 'previous', 'next'], loc='best')
        if save:
            plt.savefig(save)
        else:
            plt.show()

        # plt.plot(ts, self.counts.T)
        # plt.show()

    def draw(self):
        pos = self.pos
        # i deliberately leave the seed fixed, maybe I want same positions for networks of equal size
        nx.draw(self.graph, node_color = self.colormap, pos = pos)

        plt.show()

    def animate_last_sim(self):
        print("Generating animation...")
        start = time.time()

        assert self.net_states, "You need to run the simulation first!"
        matplotlib.interactive(False)
        fig = plt.figure()
        pos = self.pos

        nodes = nx.draw_networkx_nodes(self.graph, pos, node_color=self.net_states[0][1], node_size=3)
        edges = nx.draw_networkx_edges(self.graph, pos, width=0.1)

        # function that draws a single frame from a saved state
        def animate(idx):
            nodes.set_color(self.net_states[idx][1])
            # edges = nx.draw_networkx_edges(self.graph, pos, width=0.1)

            return nodes,
            # net_state = self.net_states[idx]

            # graph = net_state[0]
            # colormap = net_state[1]
            # fig.clf()

            # nx.draw(graph, node_color = colormap, pos = pos)

        anim = animation.FuncAnimation(fig, animate, frames=len(self.net_states), interval=1000, blit=False)

        anim.save('test.mp4')
        plt.close(fig)

        end = time.time()
        print('Saved animation. Time elapsed: {}s.'.format(end - start))

    # convenience:

    def update_state(self, id, state):
        self.graph.nodes[id]['state'] = state

    # misc

    def clustering(self):
        return nx.average_clustering(self.graph)

    def alter_clustering_coeff(self, target, epsilon):
        # to make less homogenous networks, this function redistributes edges until sufficiently close to goal

        current_coeff = nx.average_clustering(self.graph)

        budget = 10000
        counter = 0

        while abs(current_coeff - target) > epsilon and counter < budget:
            a,b = np.random.randint(0, high=self.n, size=2, dtype=int)

            neighbors_a = list(self.graph.neighbors(a))
            neighbors_b = list(self.graph.neighbors(b))


            if target > current_coeff:
                # currently coeff is too low

                if len(neighbors_a) > len(neighbors_b):
                    # a gets edge from b to increase coeff
                    c = np.random.choice(neighbors_b)
                    if (not c in neighbors_a) and len(neighbors_b) != 1:
                        # only move an edge when no edge between new partners exist AND at least 1 edge would be left

                        self.graph.remove_edge(b,c)
                        self.graph.add_edge(a,c)
                        # current_coeff = nx.average_clustering(self.graph)
                        if counter % 100 == 0: # 100 is just an idea
                            current_coeff = nx.average_clustering(self.graph) # heuristic, do it in batches
                else:
                    # b gets edge from a
                    c = np.random.choice(neighbors_a)
                    if (not c in neighbors_b) and len(neighbors_a) != 1:
                        # only move an edge when no edge between new partners exist AND at least 1 edge would be left
                        self.graph.remove_edge(a,c)
                        self.graph.add_edge(b,c)
                        # current_coeff = nx.average_clustering(self.graph)
                        if counter % 100 == 0: # 100 is just an idea
                            current_coeff = nx.average_clustering(self.graph) # heuristic, do it in batches

            else:
                # coeff is too high
                if len(neighbors_b) > len(neighbors_a): # This is the only different line, everything is flipped
                    # a gets edge from b to increase coeff
                    c = np.random.choice(neighbors_b)
                    if (not c in neighbors_a) and len(neighbors_b) != 1:
                        # only move an edge when no edge between new partners exist AND at least 1 edge would be left
                        self.graph.remove_edge(b,c)
                        self.graph.add_edge(a,c)
                        # current_coeff = nx.average_clustering(self.graph)
                        if counter % 100 == 0: # 100 is just an idea
                            current_coeff = nx.average_clustering(self.graph) # heuristic, do it in batches
                else:
                    # b gets edge from a
                    c = np.random.choice(neighbors_a)
                    if (not c in neighbors_b) and len(neighbors_a) != 1:
                        # only move an edge when no edge between new partners exist AND at least 1 edge would be left
                        self.graph.remove_edge(a,c)
                        self.graph.add_edge(b,c)
                        # current_coeff = nx.average_clustering(self.graph)
                        if counter % 100 == 0: # 100 is just an idea
                            current_coeff = nx.average_clustering(self.graph) # heuristic, do it in batches

            counter += 1
        # print(counter)
        # print(nx.average_clustering(self.graph))

        assert(counter != budget), "no success in changing clustering coefficient accordingly"

        return(current_coeff)




if __name__ == '__main__':
    p_i = 0.5
    net = Net(n = 100, p_i=p_i, p = 0.1, seed = 123, max_t=100)
    # net.draw()

    # net.sim(seed= 123, mode='quarantine')

    print(net.alter_clustering_coeff(0.09, 0.001))





    # net.animate_last_sim()



