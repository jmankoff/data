outcome_sums = Obs.sum(axis=0)     # sum across cats and dogs of each outcome type
animal_type_sums = Obs.sum(axis=1) # number of cats and number of dogs
n = np.sum(outcome_sums)         # total number of rows across cats and dogs

print "Obs", Obs
print "sums", outcome_sums
print "sums", animal_type_sums

rs = 2 # the number of animal types
cs = 6 # the number of outcome types
Exp = np.empty([rs,cs])
for r in range(0, rs):
   for c in range(0, cs):
      Exp[r,c] = (animal_type_sums[r] * outcome_sums[c])/n

print "Exp", Exp
print "Obs", Obs
X_2 = 0
for r in range(0, rs):
  for c in range(0, cs):
      diff = Exp[r, c] - Obs[r, c]
      X_2 = X_2 + (diff*diff)/Exp[r, c]
print "my CHI2: ", X_2

