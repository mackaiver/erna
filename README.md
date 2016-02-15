# Easy RuN Access (ERNA)
A collection of tools to handle FACT data and to execute jobs on a SGE/TORQUE cluster.

The erna module allows you to find datafiles and the optimal (closest) drs-files for a chosen period of time.
In the main you can choose the parameters for your search (at the moment: the beginning and the end of the requested period of time (*earliest_run* and *latest_run*), the source (*source_name*) and *timedelta_in_minutes*).
The parameter *timedelta_in_minutes* determines the maximum allowed time lag between the timestamp of the data-file and the timestamp of the appropriate drs-file. The default value is 30 minutes. Which works fine in my experience.
Dates are given in the usual FACT convention: YYYYMMDD. 

##Requirements

  - Java 1.7+
  - Python 3.5+ (srsly. 3.5 please)
  - a whole bunch of dependencies


## execute_data_processing.py

The `execute_data_processing.py` script calls the *erna* module and creates jobs for submission to a grid. This needs to be run from a server which can submit jobs to the queueing system. 
You need to provide the path to the fact-tools.jar file and the xml you want to use.
An example xml can be found in the repository. It shows how to read fact data files and how to output the result. The resulting json files are automatically collected and merged into one big outputfile. The data format of this outputfile depends on the name you choose. (e.g. big_output_file.h5, big_output_file.json, big_output_file.csv,...)

You cann call execute like this:

         python erna/execute_data_processing.py 20140101 20140130 /fhgfs/groups/app/fact/raw/ fact-tools-0.11.2 example.xml big_output_file.h5 --engine=PBS --vmem=10000 --num_jobs=60 --queue=one_day --source=Crab

When calling the `execute_list.py` script you get 


## fetch_runs.py
,
The script creates a json-file (*earliest_run_latest_run_source_name.json*), which contains the found data and drs-files
The created file can be used in conjunction with `execute_list.py` to start jobs with the files contained in the .json file.
This is useful if you don't have internet access on the machine where you submit your jobs from. *coughISDCcough*


## estimator 

The whole thing is still very much WIP (like the above). Allows you to write sklearn models to pmml format which can be read with streams.
Needs sklearn2pmml as a dependency. Install using:

      pip install  --upgrade git+https://github.com/jpmml/sklearn2pmml.git

Also needed are scipy, joblib, scikit-learn and sklearn-pandas. You might need to uninstall or unlink openblas in your system.
