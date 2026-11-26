// H35: the laptop's temperature, without a password. Built by routine/temperature.py into
// scratch/routine/thermal (clang, the first time and whenever this file changes).
// Reads the Apple Silicon temperature sensors through IOKit's HID event system (the same sensors
// Activity-Monitor-style apps read; no root needed), and macOS's own heat state (NSProcessInfo).
// Prints one line of JSON: {"cpu": hottest chip die, "cpu_avg": average of the dies,
// "battery": hottest battery sensor, "state": 0 nominal | 1 fair | 2 serious | 3 critical, "sensors": n}.
#import <Foundation/Foundation.h>

typedef struct __IOHIDEvent *IOHIDEventRef;
typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
typedef struct __IOHIDEventSystemClient *IOHIDEventSystemClientRef;
IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef);
int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef, CFDictionaryRef);
CFArrayRef IOHIDEventSystemClientCopyServices(IOHIDEventSystemClientRef);
IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
CFTypeRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef, CFStringRef);
double IOHIDEventGetFloatValue(IOHIDEventRef, int32_t);

#define TEMPERATURE 15

int main(void) {
  @autoreleasepool {
    NSDictionary *match = @{@"PrimaryUsagePage": @0xff00, @"PrimaryUsage": @5};
    IOHIDEventSystemClientRef client = IOHIDEventSystemClientCreate(kCFAllocatorDefault);
    if (!client) return 1;
    IOHIDEventSystemClientSetMatching(client, (__bridge CFDictionaryRef)match);
    CFArrayRef services = IOHIDEventSystemClientCopyServices(client);
    double cpu = -1, sum = 0, battery = -1;
    int dies = 0, n = 0;
    if (services) {
      for (CFIndex i = 0; i < CFArrayGetCount(services); i++) {
        IOHIDServiceClientRef s = (IOHIDServiceClientRef)CFArrayGetValueAtIndex(services, i);
        NSString *name = CFBridgingRelease(IOHIDServiceClientCopyProperty(s, CFSTR("Product")));
        IOHIDEventRef e = IOHIDServiceClientCopyEvent(s, TEMPERATURE, 0, 0);
        if (!e) continue;
        double t = IOHIDEventGetFloatValue(e, TEMPERATURE << 16);
        CFRelease(e);
        if (t <= 0 || t > 150) continue;  // unused sensors read below zero
        n++;
        if ([name containsString:@"tdie"]) {  // the chip's own dies (CPU and GPU clusters)
          dies++;
          sum += t;
          if (t > cpu) cpu = t;
        } else if ([name containsString:@"battery"]) {
          if (t > battery) battery = t;
        }
      }
      CFRelease(services);
    }
    long state = (long)[[NSProcessInfo processInfo] thermalState];
    printf("{\"cpu\": %.1f, \"cpu_avg\": %.1f, \"battery\": %.1f, \"state\": %ld, \"sensors\": %d}\n",
           cpu, dies ? sum / dies : -1.0, battery, state, n);
    return dies ? 0 : 2;
  }
}
