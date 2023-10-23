The feature calculation setup does not technically need to be run on the server, as the calculations by satzilla are already really fast.
I therefore added multithreading, using 6 threads by default, that calculates the features in parallel and then puts the features of all input files into one table.

## feature_setup.json
The setup file supplied to copperbench.
Example execution:
``$ python copperbench.py feature_setup.json``

The paths to the `executable` and to the `instances` file need to be adapted.
The instance lines inside the `instances` can either be of the form
``-i path_to_instance1.cnf``
or 
``-I path_to_instance_folder``

I recommend to only supply one folder OR one instance, since saving of the results does not currently support anything else.
(If you supply more, the files will overwrite each other)

## feature_configs.txt
Not really needed, but you can optionally change the name of the resulting feature file.
e.g.
``-c my_custom_filename.csv``

## feature_wrapper.sh
A small wrapper that activates the conda environment and passes the arguments to feature_runner.py
You need to adapt the paths at the start for `base_dir`, `conda_location` and `conda_env_name`.

## feature_runner.py
The main script that will run satzilla, parse the results and combine them into one single feature file.
I removed the treewidth computation for now, as that drastically reduced the dependencies - I can add it again if it is needed.
This can be run with copperbench/feature_setup.json, but can also be easily run locally like this:

``$ python feature_runner.py --instance_folder instances``

This will create a single file withh all the features of the instances inside the `instances` folder.
By default, this file is called `features.csv`.

## instance_checker.py
A small helper script to check the validity of an instance.
Currently not part of the copperbench setup, but this can be easily run locally.
Example execution:

``$ python instance_checker.py instances``

This will parse every file that ends with ".cnf" inside the `instances` folder and output a summary as a `*_report.txt` file.
It will also create a `*_dump.json` file with all information for every file to help with debugging.