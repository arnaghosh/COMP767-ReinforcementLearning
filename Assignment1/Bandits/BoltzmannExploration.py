import os, sys
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from KarmedTestbed import KarmedTestbed

class BoltzmannExploration():
	def __init__(self,bandit,temp=100,seed=13):
		self.k = bandit.k
		self.T = bandit
		self.Q = np.zeros((self.k,))
		self.trials = np.zeros((self.k,))
		self.temp = temp
		self.steps = 0
		np.random.seed(seed)

	def explore(self):
		curr_temp = self.temp/(1.+self.steps)
		H = np.exp(self.Q/curr_temp)
		prob = H/np.sum(H)
		prob_cumsum = np.cumsum(prob)
		p = np.random.uniform(0,1)
		action = np.where(prob_cumsum>p)[0][0]
		return action

	def exploit(self):
		return np.argmax(self.Q)

	def performAction(self,a):
		reward = self.T.actionPerformed(a)
		self.trials[a] += 1
		self.steps+=1
		self.Q[a] = (self.trials[a]-1)*self.Q[a]/self.trials[a] + reward/self.trials[a]
		return reward

	def regret(self,action):
		return np.max(self.T.Q)-self.T.Q[action]

	def isBestArmChosen(self,action):
		if action == np.argmax(self.T.Q):
			return 1
		return 0

	def performance(self,steps=1000,train_steps=10,test_steps=5):
		n_steps = train_steps + test_steps
		train_return = []
		test_return = []
		regret_arr = []
		optimal_action_arr = []
		# breakpoint()
		for s in range(steps):
			if s%n_steps<train_steps:
				action = self.explore()
				reward = self.performAction(action)
				train_return.append(reward)
			else:
				action = self.exploit()
				reward = self.performAction(action)
				test_return.append(reward)
			regret_arr.append(self.regret(action))
			optimal_action_arr.append(self.isBestArmChosen(action))
		train_return = np.array(train_return)
		test_return = np.array(test_return)
		test_return = np.reshape(test_return,(-1,test_steps))
		test_return = np.mean(test_return,axis=1)
		regret_arr = np.array(regret_arr)
		optimal_action_arr = np.array(optimal_action_arr)
		return train_return, test_return, regret_arr, optimal_action_arr

def evaluate_BoltzmannExploration(bandit,temp,repeats=10,total_steps=1000,train_steps=10,test_steps=5):
	train_return_arr = []
	test_return_arr = []
	regret_arr = []
	optimal_action_arr = []
	for r in tqdm(range(repeats)):
		B = BoltzmannExploration(bandit=bandit,temp=temp,seed=r)
		train_return, test_return, regret, optimal_action_chosen = B.performance(steps=total_steps, train_steps=train_steps, test_steps=test_steps)
		train_return_arr.append(train_return)
		test_return_arr.append(test_return)
		regret_arr.append(regret)
		optimal_action_arr.append(optimal_action_chosen)
	train_return_arr = np.array(train_return_arr)
	test_return_arr = np.array(test_return_arr)
	regret_arr = np.array(regret_arr)
	optimal_action_arr = np.array(optimal_action_arr)
	return train_return_arr, test_return_arr, regret_arr, optimal_action_arr

def plot_Boltzmann_hyperparam(repeats,train_steps,test_steps,total_steps,temp_range):
	bandit = KarmedTestbed(k=10)
	for t in temp_range:
		train_return_arr,test_return_arr,regret_arr, optimal_action_arr = evaluate_BoltzmannExploration(bandit=bandit,temp=t,repeats=repeats,total_steps=total_steps,train_steps=train_steps,test_steps=test_steps)
		avg_train_return = np.mean(train_return_arr,axis=0)
		sterr_train_return = np.std(train_return_arr,axis=0)/np.sqrt(np.size(train_return_arr,axis=0))
		avg_test_return = np.mean(test_return_arr,axis=0)
		sterr_test_return = np.std(test_return_arr,axis=0)/np.sqrt(np.size(test_return_arr,axis=0))
		avg_regret = np.mean(regret_arr,axis=0)
		sterr_regret = np.std(regret_arr,axis=0)/np.sqrt(np.size(regret_arr,axis=0))
		avg_optimal_action_percent = np.mean(optimal_action_arr,axis=0)
		sterr_optimal_action_percent = np.std(optimal_action_arr,axis=0)/np.sqrt(np.size(optimal_action_arr,axis=0))
		plt.figure(1)
		plt.plot(avg_train_return,label='Boltzmann T='+str(t))
		plt.fill_between(np.linspace(1,avg_train_return.shape[0],avg_train_return.shape[0]),avg_train_return-sterr_train_return,avg_train_return+sterr_train_return,alpha=0.4)
		plt.figure(2)
		plt.plot(np.linspace(train_steps,train_steps*(total_steps//(train_steps+test_steps)),total_steps//(train_steps+test_steps)),avg_test_return,label='Boltzmann T='+str(t))
		plt.fill_between(np.linspace(train_steps,train_steps*(total_steps//(train_steps+test_steps)),total_steps//(train_steps+test_steps)),avg_test_return-sterr_test_return,avg_test_return+sterr_test_return,alpha=0.4)
		plt.figure(3)
		# breakpoint()
		all_idx = np.linspace(0,total_steps-1,total_steps).astype(int)
		testing_idx = np.array([i for i in range(total_steps) if i%(train_steps+test_steps)>=train_steps])
		training_idx = np.setdiff1d(all_idx,testing_idx)
		p = plt.plot(training_idx,avg_regret[training_idx],label='Boltzmann T='+str(t)+'(Train)')
		plt.fill_between(training_idx,avg_regret[training_idx]-sterr_regret[training_idx],avg_regret[training_idx]+sterr_regret[training_idx],alpha=0.4)
		plt.errorbar(testing_idx,avg_regret[testing_idx],yerr=sterr_regret[testing_idx],linestyle='None',marker='*',markersize=10,color=p[0].get_color(),label='Boltzmann T='+str(t)+'(Test)')
		plt.figure(4)
		p = plt.plot(training_idx,avg_optimal_action_percent[training_idx],label='Boltzmann T='+str(t)+'(Train)')
		plt.fill_between(training_idx,avg_optimal_action_percent[training_idx]-sterr_optimal_action_percent[training_idx],avg_optimal_action_percent[training_idx]+sterr_optimal_action_percent[training_idx],alpha=0.4)
		plt.errorbar(testing_idx,avg_optimal_action_percent[testing_idx],yerr=sterr_optimal_action_percent[testing_idx],linestyle='None',marker='*',markersize=10,color=p[0].get_color(),label='Boltzmann T='+str(t)+'(Test)')
	plt.figure(1)
	plt.title('Average Training return')
	plt.xlabel('Steps')
	plt.ylabel('Average reward')
	plt.legend()
	plt.figure(2)
	plt.title('Average Testing return')
	plt.xlabel('Steps')
	plt.ylabel('Average reward')
	plt.legend()
	plt.figure(3)
	plt.title('Average Regret')
	plt.xlabel('Steps')
	plt.ylabel('Average regret')
	plt.legend()
	plt.figure(4)
	plt.title('Percentage of optimal action choice')
	plt.xlabel('Steps')
	plt.ylabel('% Optimal Action')
	plt.legend()
	plt.show()
	
if __name__ =='__main__':
	plot_Boltzmann_hyperparam(repeats=50,train_steps=10,test_steps=5,total_steps=1000,temp_range=[10,50,100,500,1000])