/*********************                                                        */
/*! \file GetCPUData.h
** \verbatim
** Top contributors (to current version):
**   Haoze Wu
** This file is part of the Marabou project.
** Copyright (c) 2017-2019 by the authors listed in the file AUTHORS
** in the top-level source directory) and their institutional affiliations.
** All rights reserved. See the file COPYING in the top-level source
** directory for licensing information.\endverbatim
**
** [[ Add lengthier description here ]]

**/

#ifndef __GetCPUData_h__
#define __GetCPUData_h__

#if defined(__linux__)
#include <sched.h>
#define getCPUId(cpu)                                                          \
  {                                                                            \
    cpu = sched_getcpu();                                                      \
  }
#elif __APPLE__
#if (!defined(__arm64__))
#include <cpuid.h>

#define CPUId(INFO, LEAF, SUBLEAF)                                             \
  __cpuid_count(LEAF, SUBLEAF, INFO[0], INFO[1], INFO[2], INFO[3])
#define getCPUId(cpu)                                                          \
  {                                                                            \
    uint32_t CPUInfo[4];                                                       \
    CPUId(CPUInfo, 1, 0);                                                      \
    if ((CPUInfo[3] & (1 << 9)) == 0) {                                        \
      cpu = -1;                                                                \
    } else {                                                                   \
      cpu = (unsigned)CPUInfo[1] >> 24;                                        \
    }                                                                          \
    if (cpu < 0)                                                               \
      cpu = 0;                                                                 \
  }
#else
#include <string.h>
#include <sys/sysctl.h>
#include <sys/types.h>

#define getCPUId(cpu)                                                          \
  {                                                                            \
    int hasNeon = 0;                                                           \
    size_t size = sizeof(hasNeon);                                             \
    if (sysctlbyname("hw.optional.neon", &hasNeon, &size, NULL, 0) == 0) {     \
      if (hasNeon) {                                                           \
        cpu = 1;                                                               \
      } else {                                                                 \
        cpu = -1;                                                              \
      }                                                                        \
    } else {                                                                   \
      cpu = -1;                                                                \
    }                                                                          \
                                                                               \
    if (cpu < 0)                                                               \
      cpu = 0;                                                                 \
  }
#endif
#else
#define getCPUId(cpu) "#"
#endif

#endif // __GetCPUData_h__

//
// Local Variables:
// compile-command: "make -C ../.. "
// tags-file-name: "../../TAGS"
// c-basic-offset: 4
// End:
//
