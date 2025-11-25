import sys
print(f"Python Executable: {sys.executable}")

try:
    from ortools.sat.python import cp_model
    print("OR-Tools is installed and importable!")
    
    # Simple test solve
    model = cp_model.CpModel()
    x = model.NewBoolVar('x')
    model.Add(x == 1)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.OPTIMAL:
        print("Solver is working correctly!")
    else:
        print("Solver failed basic test.")
        
except ImportError as e:
    print(f"OR-Tools IMPORT ERROR: {e}")
    print("Try running: pip install ortools")
except Exception as e:
    print(f"UNEXPECTED ERROR: {e}")
