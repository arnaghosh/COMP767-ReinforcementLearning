import os, sys
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from mountainCar import MountainCar
from asymmetricTileCoding import AsymmetricTileCoding

class Control_SARSALambda():
	def __init__(self,environment,functionApprox='linear',traces='replacing'):
		self.environment = environment
		self.functionApprox = functionApprox
		self.traces = traces

	def construct_flattened_tile_idx(self,tileCode,bins=None):
		tilings = tileCode.shape[0]
		dims = tileCode.shape[1]
		if bins is None:
			# bins is equal to the number of tilings
			bins = tilings
		'''
		flattened_tile_idxs = []
		for tile in range(tilings):
			code = tileCode[tile]
			idx = np.sum(code*(np.logspace(dims-1,0,dims,base=bins)))
			flattened_tile_idxs.append((bins**dims)*tile+idx)
		# Single line implementation below :)
		'''
		flattened_tile_idxs = np.array([(bins**dims)*tile+np.sum(tileCode[tile]*(np.logspace(dims-1,0,dims,base=bins))) for tile in range(tilings)]).astype(int)
		return flattened_tile_idxs

	def estimate_Q_function_approx(self,alpha,lamda,episodes=25,bins=8,tilings=8,seed=13,verbose=False):
		ATC = AsymmetricTileCoding(dims=self.environment.dims,bins=bins,tilings=tilings,state_limits=[[0,0],[1,1]],seed=seed)
		if self.functionApprox == 'linear':
			weights = np.zeros((tilings*(bins**self.environment.dims),len(self.environment.actions)))
		else:
			raise NotImplementedError
		weights = self.SARSA_lambda(tileCoding=ATC,func=weights,alpha=alpha,lamda=lamda,episodes=episodes,verbose=verbose)
		return ATC,weights

	def apply_function_approx(self,func,action,tileCode,bins=None):
		action_idx = np.where(np.array(self.environment.actions)==action)[0][0]
		if self.functionApprox=='linear':
			return np.sum(func[self.construct_flattened_tile_idx(tileCode,bins),action_idx])
		else:
			raise NotImplementedError

	def getTileCode(self,tileCoding):
		tileCode = tileCoding.getCodedState(self.environment.getNormalizedState())
		return tileCode

	def epsilon_greedy(self,tileCoding,func,epsilon=0.1):
		'''
		Return: curr_state(tile coded),curr_action pair
		'''
		p = np.random.rand()
		tileCode = self.getTileCode(tileCoding)
		if p>epsilon:
			# do greedy action
			q_arr = np.array([self.apply_function_approx(func=func,action=a,tileCode=tileCode,bins=tileCoding.bins) for a in self.environment.actions])
			action = self.environment.actions[np.argmax(q_arr)]
		else:
			# take random exploratory action
			action = self.environment.actions[np.random.randint(0,len(self.environment.actions))]
		return tileCode,action

	def SARSA_lambda(self,tileCoding,func,alpha,lamda,epsilon=0.1,episodes=25,verbose=False):
		for e in tqdm(range(episodes)):
			if verbose:
					print("Starting episode {}".format(e+1))
			self.environment.reset()
			curr_tileCode,curr_action = self.epsilon_greedy(tileCoding,func,epsilon)
			max_T = 2000		# max time steps to run an episode
			eligibility_trace = np.zeros(func.shape)
			for iter in range(max_T):
				reward,is_terminated = self.environment.takeAction(curr_action)
				if self.functionApprox=='linear':
					SARSA_error = reward - self.apply_function_approx(func,curr_action,curr_tileCode,bins=tileCoding.bins)
					curr_action_idx = np.where(np.array(self.environment.actions)==curr_action)[0][0]
					weight_derivative = np.zeros(func.shape)
					weight_derivative[self.construct_flattened_tile_idx(curr_tileCode,tileCoding.bins),curr_action_idx]=1
				else:
					raise NotImplementedError
				if self.traces =='replacing':
					eligibility_trace = np.maximum(eligibility_trace,weight_derivative)
				elif self.traces =='accumulating':
					eligibility_trace = 1 + weight_derivative
				else:
					raise NotImplementedError
				if not is_terminated:
					next_tileCode,next_action = self.epsilon_greedy(tileCoding,func,epsilon)
					SARSA_error += self.environment.gamma*self.apply_function_approx(func,next_action,next_tileCode,bins=tileCoding.bins)
				if verbose:
					print(curr_tileCode,np.where(eligibility_trace>0))
					print(SARSA_error,np.max(eligibility_trace),np.shape(eligibility_trace))
					plt.subplot(311);plt.plot(func[:,0],'*'); 
					plt.subplot(312);plt.plot(func[:,1],'*'); 
					plt.subplot(313);plt.plot(func[:,2],'*'); plt.show()
					self.plot_estimated_value_func(tileCoding,func)
				func += (alpha/tileCoding.tilings)*SARSA_error*eligibility_trace
				if is_terminated:
					break
				eligibility_trace = lamda*self.environment.gamma*eligibility_trace
				curr_tileCode = next_tileCode
				curr_action = next_action
		return func

	def plot_estimated_value_func(self,tileCoding,func):
		lower_limit = self.environment.state_min
		upper_limit = self.environment.state_max
		sampled_states = np.random.uniform(0,1,(50,self.environment.dims))
		# X, Y = np.meshgrid(sampled_states[:,0],sampled_states[:,1])
		# print([s.shape for s in zip(X,Y)])
		estimated_val_back = np.array([self.apply_function_approx(func,-1,tileCoding.getCodedState(s)) for s in sampled_states])
		estimated_val_stationary = np.array([self.apply_function_approx(func,0,tileCoding.getCodedState(s)) for s in sampled_states])
		estimated_val_forward = np.array([self.apply_function_approx(func,1,tileCoding.getCodedState(s)) for s in sampled_states])
		from mpl_toolkits import mplot3d
		ax1=plt.subplot(311,projection='3d'); scatt = ax1.scatter(sampled_states[:,0],sampled_states[:,1],estimated_val_back,c=estimated_val_back,cmap='viridis'); plt.colorbar(scatt)
		ax2=plt.subplot(312,projection='3d'); scatt = ax2.scatter(sampled_states[:,0],sampled_states[:,1],estimated_val_stationary,c=estimated_val_stationary,cmap='viridis'); plt.colorbar(scatt)
		ax3=plt.subplot(313,projection='3d'); scatt = ax3.scatter(sampled_states[:,0],sampled_states[:,1],estimated_val_forward,c=estimated_val_forward,cmap='viridis'); plt.colorbar(scatt)
		plt.show()

	'''
	def calculate_value_func_MSE(self,sparseCoding,func):
		lower_limit = self.environment.state_min
		upper_limit = self.environment.state_max
		sampled_states = np.linspace(lower_limit,upper_limit,21)
		estimated_val = np.array([self.apply_function_approx(func,sparseCoding.getCodedState(s)) for s in sampled_states])
		mse = np.mean((sampled_states-estimated_val)**2)
		return mse
	'''
	
if __name__=='__main__':
	M = MountainCar()
	control_SARSA = Control_SARSALambda(environment=M,functionApprox='linear',traces='replacing')
	ATC,func_approximator = control_SARSA.estimate_Q_function_approx(alpha=0.1,lamda=0,episodes=20,verbose=False)
	control_SARSA.plot_estimated_value_func(ATC,func_approximator)
	'''
	num_alpha = 25
	num_lamda = 6
	colors = ['darkviolet','blue','green','gold','darkorange','red']
	lamda_range = np.linspace(0,1,num_lamda)
	alpha_range = np.linspace(0,1,num_alpha)
	seeds = 50
	R = RandomWalker()
	pred_TD = Prediction_TDLambda(environment=R,policy=None,functionApprox='linear')
	mean_mse_arr = np.zeros((num_lamda,num_alpha))
	std_mse_arr = np.zeros((num_lamda,num_alpha))
	for l_idx,lamda in tqdm(enumerate(lamda_range)):
		for a_idx,alpha in enumerate(alpha_range):
			mse_arr = np.zeros((seeds,))
			for seed in range(seeds):
				SCC,val_func_estimator = pred_TD.estimate_value_function_approx(alpha=alpha,lamda=lamda,episodes=80,seed=seed,verbose=False)
				mse_arr[seed] = pred_TD.calculate_value_func_MSE(SCC,val_func_estimator)
			mean_mse_arr[l_idx,a_idx] = np.mean(mse_arr)
			std_mse_arr[l_idx,a_idx] = np.std(mse_arr)/np.sqrt(seeds)
	# pred_TD.plot_estimated_value_func(SCC,val_func_estimator)
		plt.plot(alpha_range,mean_mse_arr[l_idx],color=colors[l_idx],label="$\lambda$={:.3f}".format(lamda))
		plt.fill_between(alpha_range,mean_mse_arr[l_idx]-std_mse_arr[l_idx],mean_mse_arr[l_idx]+std_mse_arr[l_idx],color=colors[l_idx],alpha=0.4)
	plt.ylim(top=0.6)
	plt.legend(fontsize=14)
	plt.xticks(fontsize=13)
	plt.yticks(fontsize=13)
	plt.xlabel('$\\alpha$',size=14)
	plt.ylabel('Mean Squared Error',size=14)
	plt.title('Performance of TD($\lambda$) with accumulating traces',fontsize=16)
	plt.show()
	'''