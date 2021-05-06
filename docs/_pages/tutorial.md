---
title: Tutorial
permalink: /tutorial
---

This page contains materials for the VTK-m tutorial, which will be presented on Sunday, October 20th at the VIS19 conference in Vancouver, Canada. Attendees can get the slides [HERE](https://m.vtk.org/images/f/f3/VTKm_Tutorial_VIS19.pptx) and the user guide is [HERE](https://m.vtk.org/images/c/c9/VTKmUsersGuide-1-5.pdf).

**There are two options for running code:**
1. Building VTK-m on your own machine.
2. Running our VirtualBox image with VTK-m installed.

Sections below describe how to pursue each of these options.

------

## Download and build VTK-m

**The process to build VTK-m:**

- Download V1.5.0 [here](https://m.vtk.org/index.php/VTK-m_Releases#VTK-m_Version_1.5.0).
  - (note the build page assumes you will be accessing the master via a git clone, but we encourage you to use the released version for the tutorial)
- Do not enable the TBB, OpenMP or CUDA support, at least at first.
  - (we stand behind our support for these backends, but it is good to start simple)

In all, your process on Unix/Mac should be something like:
~~~
# (download VTK-m 1.5.0)
# tar xvfz vtk-m-v1.5.0.tar.gz
# mkdir build install # out of source build
# cd build
# cmake -DCMAKE_INSTALL_PREFIX=../install -DVTKm_ENABLE_TESTING:BOOL=OFF ../vtk-m-v1.5.0
# make -j4
# make install
~~~

The main instructions to download and build are [here <i class="ri-external-link-fill"></i>](https://gitlab.kitware.com/vtk/vtk-m/blob/master/README.md#building). That said, we recommend following the instructions above.


**The process to build code examples:**
- For V1.5.0 (which was used for the tutorial), download the examples for the tutorial [here](https://m.vtk.org/images/e/ea/VTKm_tutorial_examples.tar.gz)
- For V1.6.0 (the release after the tutorial), download the examples for the tutorial from [github <i class="ri-external-link-fill"></i>](https://github.com/uo-cdux/vtk-m-tutorial)

Your process on Unix/Mac should be something like:
~~~
# (downloads from above)
# export D=/path/to/where/your/browser/downloads/files
# mkdir VTKm_tutorial_examples    # should be peer to build/install
# cd VTKm_tutorial_examples
# cp $D/VTKm_tutorial_examples.tar .
# tar xvf VTKm_tutorial_examples.tar.gz # places tutorial files in $PWD
# cmake . -DCMAKE_PREFIX_PATH="<path_to_vtkm-installation>/"
--> if you did a "make install" and this directory is peer to the install directory, then it would be
--> # cmake . -DCMAKE_PREFIX_PATH=../install
# make
# ./tut_io # run 1st example
# ls out_io.vtk # confirms 1st example successfully completed
~~~

------

## Download Virtual Box image with VTK-m

The Virtual Box image with VTK-m installed can be found [here <i class="ri-external-link-fill"></i>](https://www.dropbox.com/s/36hn0no3jhn9wra/VTKm_tutorial.ova?dl=0).

To be able to use this image you'll need to have the Virtual Box software installed. Please follow the instructions provided [here <i class="ri-external-link-fill"></i>](https://www.virtualbox.org/wiki/Downloads).

The internet connection at the tutorial venue may discourage the requested downloads, in that case please ask the presenters for a flash drive with the required material.

The username/password to access the material on the VM are `vtkm/vtkm`.

- VTK-m source code and build can be accessed in the "/home/vtkm/Software/VTK-m/"
  - The source code is available in the "vtk-m-v1.5.0" directory
  - The build files are available in the "build" directory
  - VTK-m has already been installed for use by the example code
