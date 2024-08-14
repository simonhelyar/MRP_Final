
import gurobipy as gp
import numpy as np
from gurobipy import GRB

#PARAMETERS

pred = np.array([6.235461109602136, 5.660681113822478, 5.691522006935785, 5.0989242170014375, 6.1708063631519945, 6.077117427899992, 6.7003846791552695, 7.539736044412286, 7.6778192311949365, 8.689052596857312])

C = np.array([[10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000],
     [10000000,5000000,2500000]])


R = np.array([[2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8],
     [2.1,1.1,0.8]
     ])

E = np.array([[0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1],
              [0.75,0.6,0.5,0.2, 0.1]
              ])

#SET BUDGET AMOUNT
#B = 200000000
#B = 100000000
B = 50000000

target = np.array([5,5,5,5,5,5,5,5,5,5])
I = [0,1,2,3,4,5,6,7,8,9]
J = [0,1,2]
p = [1/5,1/5,1/5,1/5,1/5]
S = [0,1,2,3,4]

penalty = np.array([[10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000],
                    [10000000,7500000,5000000,2500000,1000000]])

m = gp.Model("2SP")
m.setParam('OutputFlag', 0)

#DECISION VARIABLES
x = m.addVars(10,3, vtype=GRB.BINARY, name='x')
actual = m.addVars(10,5,lb=0, name = 'actual')
incr = m.addVars(10,5,lb=0, name = 'incr')

#OBJECTIVE FUNCTION
m.setObjective(gp.quicksum(C[i,j] * x[i,j] for i in I for j in J) +
               gp.quicksum(p[s] * gp.quicksum(penalty[i,s] * incr[i,s] for i in I) for s in S), GRB.MINIMIZE)

#CONTRAINTS
m.addConstr(gp.quicksum(C[i,j] * x[i,j] for i in I for j in J) <= B)


for i in I:
    for s in S:
        m.addConstr(actual[i,s] == pred[i] + E[i,s] - gp.quicksum(R[i,j] * x[i,j] for j in J))
        
for i in I:
    for s in S:
        m.addConstr(actual[i,s] <= target[i] + incr[i,s])
        
m.optimize()

#GET OPTIMIZATION OUTPUT VALUES
x_output = np.array(0)
act = np.array(0)
inc = np.array(0)

if m.SolCount > 0:
    x_temp = []
    act_temp = []
    inc_temp = []
    for i in range(10):
        a = []
        b = []
        c = []
        for p in range(len(J)):
            a.append(x[i,p].X)
        for j in range(len(S)):
            b.append(actual[i,j].X)
            c.append(incr[i,j].X)

        x_temp.append(a)
        act_temp.append(b)
        inc_temp.append(c)
    
    x_output = np.array(x_temp)
    act = np.array(act_temp)
    inc = np.array(inc_temp)

print('Policy Decisions:')
print(x_output)
print('Actual PM2.5 Values:')
print(act)
print('Increase Values:')
print(inc)