##############################################################################
# Copyright (c) 2013-2016, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory.
#
# This file is part of Spack.
# Created by Todd Gamblin, tgamblin@llnl.gov, All rights reserved.
# LLNL-CODE-647188
#
# For details, see https://github.com/llnl/spack
# Please also see the LICENSE file for our notice and the LGPL.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License (as
# published by the Free Software Foundation) version 2.1, February 1999.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the IMPLIED WARRANTY OF
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the terms and
# conditions of the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
##############################################################################

#
# This is a template package file for Spack.  We've put "FIXME"
# next to all the things you'll want to change. Once you've handled
# them, you can save this file and test your package like this:
#
#     spack install test_imb
#
# You can edit this file again by typing:
#
#     spack edit test_imb
#
# See the Spack documentation for more information on packaging.
# If you submit this package back to Spack as a pull request,
# please first remove this boilerplate and all FIXME comments.
#
from spack import *

class TestImb(Package):
    """The Intel MPI Benchmarks perform a set of MPI performance measurements for point-to-point and global communication operations for a range of message sizes"""
    homepage = "https://software.intel.com/en-us/articles/intel-mpi-benchmarks/"
    url      = "https://software.intel.com/sites/default/files/managed/a3/b2/IMB_4.1.tgz"

    version('4.1', 'c69ea72a5c101cf1292061dfd0223bc1')

    depends_on("mpi")

    patch('mpiicc.patch')
    def install(self, spec, prefix):

        with working_dir('src'):
            make("-f","make_ict", parallel=False)
        mkdirp(prefix.bin)
        imb = join_path(self.stage.source_path, 'src/IMB-MPI1')
        install(imb,prefix.bin)

