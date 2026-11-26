// H44: the totals Activity Monitor shows, read without a password. Built by routine/stats.py with clang
// into scratch/routine/stats the first time and whenever this file changes. Prints one line of JSON with
// the raw counters; stats.py turns them into a reading per minute (the counters only ever go up, so the
// difference with the last minute is that minute's use).
//   cpu: user, system, idle, nice ticks (all cores together, host_statistics)
//   gpu: the GPU's own "Device Utilization %" (IOAccelerator's PerformanceStatistics), averaged over a second
//   mem: total bytes, page size and the page counts Activity Monitor adds up for "Memory Used"
//   disk: bytes read and written by all internal disks (IOBlockStorageDriver's Statistics)
//   net: bytes in and out on all interfaces except the loopback (64-bit counters, NET_RT_IFLIST2)
#import <Foundation/Foundation.h>
#import <IOKit/IOKitLib.h>
#include <mach/mach.h>
#include <sys/sysctl.h>
#include <net/if.h>
#include <net/route.h>
#include <unistd.h>

static long long num(id v) { return [v isKindOfClass:[NSNumber class]] ? [v longLongValue] : -1; }

int main(void) {
  @autoreleasepool {
    NSMutableDictionary *out = [NSMutableDictionary dictionary];

    host_cpu_load_info_data_t cpu;
    mach_msg_type_number_t n = HOST_CPU_LOAD_INFO_COUNT;
    if (host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, (host_info_t)&cpu, &n) == KERN_SUCCESS)
      out[@"cpu"] = @{@"user": @(cpu.cpu_ticks[CPU_STATE_USER]), @"system": @(cpu.cpu_ticks[CPU_STATE_SYSTEM]),
                      @"idle": @(cpu.cpu_ticks[CPU_STATE_IDLE]), @"nice": @(cpu.cpu_ticks[CPU_STATE_NICE])};

    vm_statistics64_data_t vm;
    n = HOST_VM_INFO64_COUNT;
    vm_size_t page = 0;
    host_page_size(mach_host_self(), &page);
    uint64_t total = 0;
    size_t len = sizeof(total);
    sysctlbyname("hw.memsize", &total, &len, NULL, 0);
    if (host_statistics64(mach_host_self(), HOST_VM_INFO64, (host_info64_t)&vm, &n) == KERN_SUCCESS)
      out[@"mem"] = @{@"total": @(total), @"page": @(page), @"internal": @(vm.internal_page_count),
                      @"purgeable": @(vm.purgeable_count), @"wired": @(vm.wire_count),
                      @"compressed": @(vm.compressor_page_count), @"free": @(vm.free_count),
                      @"swapouts": @(vm.swapouts)};

    // The GPU's use jumps from moment to moment, so it's read ten times over a second and averaged.
    long long gpu = -1, rd = 0, wr = 0, sum = 0;
    int got = 0;
    io_iterator_t it;
    for (int i = 0; i < 10; i++) {
      if (i) usleep(100000);
      long long best = -1;
      if (IOServiceGetMatchingServices(kIOMainPortDefault, IOServiceMatching("IOAccelerator"), &it) == KERN_SUCCESS) {
        io_object_t o;
        while ((o = IOIteratorNext(it))) {
          CFTypeRef p = IORegistryEntryCreateCFProperty(o, CFSTR("PerformanceStatistics"), kCFAllocatorDefault, 0);
          if (p) {
            NSDictionary *d = CFBridgingRelease(p);
            long long u = num(d[@"Device Utilization %"]);
            if (u > best) best = u;
          }
          IOObjectRelease(o);
        }
        IOObjectRelease(it);
      }
      if (best >= 0) { sum += best; got++; }
    }
    if (got) gpu = (sum + got / 2) / got;
    if (gpu >= 0) out[@"gpu"] = @(gpu);
    if (IOServiceGetMatchingServices(kIOMainPortDefault, IOServiceMatching("IOBlockStorageDriver"), &it) == KERN_SUCCESS) {
      io_object_t o;
      while ((o = IOIteratorNext(it))) {
        CFTypeRef p = IORegistryEntryCreateCFProperty(o, CFSTR("Statistics"), kCFAllocatorDefault, 0);
        if (p) {
          NSDictionary *d = CFBridgingRelease(p);
          long long r = num(d[@"Bytes (Read)"]), w = num(d[@"Bytes (Write)"]);
          if (r > 0) rd += r;
          if (w > 0) wr += w;
        }
        IOObjectRelease(o);
      }
      IOObjectRelease(it);
    }
    out[@"disk"] = @{@"read": @(rd), @"written": @(wr)};

    int mib[6] = {CTL_NET, PF_ROUTE, 0, 0, NET_RT_IFLIST2, 0};
    size_t sz = 0;
    unsigned long long in = 0, ob = 0;
    if (sysctl(mib, 6, NULL, &sz, NULL, 0) == 0 && sz > 0) {
      char *buf = malloc(sz);
      if (buf && sysctl(mib, 6, buf, &sz, NULL, 0) == 0) {
        for (char *p = buf; p < buf + sz;) {
          struct if_msghdr *ifm = (struct if_msghdr *)p;
          if (ifm->ifm_msglen == 0) break;
          if (ifm->ifm_type == RTM_IFINFO2) {
            struct if_msghdr2 *m2 = (struct if_msghdr2 *)p;
            if (!(m2->ifm_flags & IFF_LOOPBACK)) {
              in += m2->ifm_data.ifi_ibytes;
              ob += m2->ifm_data.ifi_obytes;
            }
          }
          p += ifm->ifm_msglen;
        }
      }
      free(buf);
    }
    out[@"net"] = @{@"in": @(in), @"out": @(ob)};

    NSData *j = [NSJSONSerialization dataWithJSONObject:out options:0 error:nil];
    printf("%s\n", [[[NSString alloc] initWithData:j encoding:NSUTF8StringEncoding] UTF8String]);
  }
  return 0;
}
