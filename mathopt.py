from ortools.math_opt.python import mathopt
model = mathopt.Model(name="example")
x = model.add_variable(0.0, 10.0, name="x")
model.add_linear_constraint(2 * x <= 5, name="c1")
model.maximize(3 * x)
params = mathopt.SolveParameters()
result = mathopt.solve(model, mathopt.SolverType.GLOP, params=params)
print(f"Optimal value: {result.objective_value()}")