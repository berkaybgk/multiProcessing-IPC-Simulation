This is the project folder of the 2nd assignment of the CMPE300 class.

It features the source code of the implementation, and the input/output files.

You can check the report file for the implementation details. What we have done basically is:
We used the mpi4py package to achieve IPC and use parallel programming to simulate a battle environment.

You can follow these steps to run the code and see the result of the simulation:

After making sure that you have OpenMPI and python3 installed in your system and downloading the folder

```bash
# install the mpi4py package in your environment
pip install mpi4py

# cd into the project folder
cd src

# run the main.py file with the following command, giving the processor count and the input/output file paths as arguments
mpiexec -n 5 main.py ./io/input1.txt ./io/output1.txt
```


You can change the -n parameter based on the number of processors available in your system.
After executing the main.py, you can find the output under src/io/output1.txt

If you want to change the input, you can just replace the input1.txt under src/io to your own input.

---

Berkay Bugra Gok, Talha Ozdogan
