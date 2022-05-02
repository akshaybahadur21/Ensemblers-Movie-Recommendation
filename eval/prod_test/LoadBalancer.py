import os
import random


class LoadBalancer:
    def __init__(self):
        self.thresh = 0.5

    @staticmethod
    def heart_beat(ip_addr):
        return os.system('nc -vz ' + ip_addr) == 0

    def balance(self):
        knn_server_up = self.heart_beat('172.17.0.4 9001')
        contnet_server_up = self.heart_beat('172.17.0.5 9002')
        if knn_server_up and contnet_server_up:
            if random.uniform(0, 1) < self.thresh:
                return "http://172.17.0.4:9001/recommend/"
            else:
                return "http://172.17.0.5:9002/recommend/"
        elif knn_server_up:
            return "http://172.17.0.4:9001/recommend/"
        elif contnet_server_up:
            return "http://172.17.0.5:9002/recommend/"
        else:
            return None