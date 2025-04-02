/**
 * @file	tdvm_debug.c
 * @author	cpio
 * @date	6 Sept 2021
 * @version	0.1
 * @brief	porting from https://gitlab.com/kvm-unit-tests/kvm-unit-tests/-/blob/master/x86/debug.c
 *		tests will be run at kernel init stage when the module is loaded,
 *		the results appears in the kernel log with keyword "cpio".
*/

#include <linux/module.h>	/* Needed by all modules */
#include <linux/kernel.h>	/* Needed for KERN_INFO */
#include <linux/init.h>		/* Needed for the macros */
#include <linux/ptrace.h>
#include <asm/traps.h>
#include <asm/segment.h>
#include <asm/debugreg.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("cpio");
MODULE_DESCRIPTION("tdvm kernel debugging unittest");
MODULE_VERSION("0.1");

#define LOG_PREFIX "cpio: "
#define PASS "PASS: "
#define FAIL "FAIL: "
#define p_pass(fmt, ...) printk(KERN_INFO LOG_PREFIX PASS fmt, ##__VA_ARGS__)
#define p_fail(fmt, ...) printk(KERN_INFO LOG_PREFIX FAIL fmt, ##__VA_ARGS__)
#define p_info(fmt, ...) printk(KERN_INFO LOG_PREFIX fmt, ##__VA_ARGS__)

extern volatile uint tdvm_test_stage;
extern volatile bool tdvm_got_ud;
extern volatile uint tdvm_n;
extern volatile ulong tdvm_db_addr[10], tdvm_dr6[10];
extern volatile ulong tdvm_bp_addr;

static unsigned long cr4;
static unsigned long start;
static volatile unsigned long value;

static void report(bool, char *);
static inline void write_cr4(ulong);
static inline ulong read_cr4(void);
static inline void write_dr0(void *);
static inline void write_dr1(void *);
static inline void write_dr4(ulong);
static inline ulong read_dr4(void);
static inline void write_dr6(ulong);
static inline void write_dr7(ulong);

static void test1(void)
{
	cr4 = read_cr4();
	write_cr4(cr4 & ~X86_CR4_DE);
	write_dr4(0);
	write_dr6(0xffff4ff2);

	report(read_dr4() == 0xffff4ff2 && !tdvm_got_ud,
		   "reading DR4 with CR4.DE == 0");
}

static void test2(void)
{
	cr4 = read_cr4();
	write_cr4(cr4 | X86_CR4_DE);
	read_dr4();
	report(tdvm_got_ud,
		   "reading DR4 with CR4.DE == 1");
}

static void test3(void)
{
	extern unsigned char sw_bp;
	tdvm_bp_addr = 1;
	asm volatile("int3; sw_bp:");
	report(tdvm_bp_addr == (unsigned long)&sw_bp,
		   "sw breakpoint #BP");

}

static void test4(void)
{
		extern unsigned char hw_bp1;
	tdvm_n = 0;
	write_dr6(DR6_RESERVED);
	write_dr0(&hw_bp1);
	write_dr7(0x00000402);
	asm volatile("hw_bp1: nop");
	p_info("n:%d db_addr:%lx hw_bp1:%lx tdvm_dr6:%lx",
		tdvm_n, tdvm_db_addr[0], (unsigned long)&hw_bp1, tdvm_dr6[0]);
	report(tdvm_n == 1 &&
		   tdvm_db_addr[0] == ((unsigned long)&hw_bp1) &&
		   tdvm_dr6[0] == 0xffff0ff1,
		   "hw breakpoint (test that dr6.BS is not set)");
}

static void test5(void)
{
	extern unsigned char hw_bp2;
	tdvm_n = 0;
	write_dr0(&hw_bp2);
	write_dr6(0x00004002);
	asm volatile("hw_bp2: nop");
	report(tdvm_n == 1 &&
		   tdvm_db_addr[0] == ((unsigned long)&hw_bp2) && tdvm_dr6[0] == 0xffff4ff1,
		   "hw breakpoint (test that dr6.BS is not cleared)");
}

static void test6(void)
{
	tdvm_n = 0;
	write_dr6(0);
	asm volatile(
		"pushf\n\t"
		"pop %%rax\n\t"
		"or $(1<<8),%%rax\n\t"
		"push %%rax\n\t"
		"lea (%%rip),%0\n\t"
		"popf\n\t"
		"and $~(1<<8),%%rax\n\t"
		"push %%rax\n\t"
		"popf\n\t"
		: "=r" (start) : : "rax");
	report(tdvm_n == 3 &&
		   tdvm_db_addr[0] == start + 1 + 6 && tdvm_dr6[0] == 0xffff4ff0 &&
		   tdvm_db_addr[1] == start + 1 + 6 + 1 && tdvm_dr6[1] == 0xffff4ff0 &&
		   tdvm_db_addr[2] == start + 1 + 6 + 1 + 1 && tdvm_dr6[2] == 0xffff4ff0,
		   "single step");
}

static void test7(void)
{
	/*
	 * cpuid and rdmsr (among others) trigger VM exits and are then
	 * emulated. Test that single stepping works on emulated instructions.
	 */
	int i;
	tdvm_n = 0;
	write_dr6(0);
	asm volatile(
		"pushf\n\t"
		"pop %%rax\n\t"
		"or $(1<<8),%%rax\n\t"
		"push %%rax\n\t"
		"lea (%%rip),%0\n\t"
		"popf\n\t"
		"and $~(1<<8),%%rax\n\t"
		"push %%rax\n\t"
		"xor %%rax,%%rax\n\t"
		"cpuid\n\t"
		"movl $0x1a0,%%ecx\n\t"
		"rdmsr\n\t"
		"popf\n\t"
		: "=r" (start) : : "rax", "ebx", "ecx", "edx");
	p_info("%d %lx", tdvm_n, start);
	for (i=0; i < tdvm_n; i++)
		p_info("%lx", tdvm_db_addr[i]);
	report(tdvm_n == 7 &&
		   tdvm_db_addr[0] == start + 1 + 6 && tdvm_dr6[0] == 0xffff4ff0 &&
		   tdvm_db_addr[1] == start + 1 + 6 + 1 && tdvm_dr6[1] == 0xffff4ff0 &&
		   tdvm_db_addr[2] == start + 1 + 6 + 1 + 3 && tdvm_dr6[2] == 0xffff4ff0 &&
		   tdvm_db_addr[3] == start + 1 + 6 + 1 + 3 + 2 && tdvm_dr6[3] == 0xffff4ff0 &&
		   tdvm_db_addr[4] == start + 1 + 6 + 1 + 3 + 2 + 5 && tdvm_dr6[4] == 0xffff4ff0 &&
		   tdvm_db_addr[5] == start + 1 + 6 + 1 + 3 + 2 + 5 + 2 && tdvm_dr6[5] == 0xffff4ff0 &&
		   tdvm_db_addr[6] == start + 1 + 6 + 1 + 3 + 2 + 5 + 2 + 1 && tdvm_dr6[6] == 0xffff4ff0,
		   "single step emulated instructions");
}

static void test8(void)
{
	extern unsigned char hw_wp1;
	tdvm_n = 0;
	write_dr1((void *)&value);
	write_dr7(0x00d0040a); // 4-byte write

	asm volatile(
		"mov $42,%%rax\n\t"
		"mov %%rax,%0\n\t; hw_wp1:"
		: "=m" (value) : : "rax");
	p_info("n:%d db_addr:%lx hw_wp1:%lx tdvm_dr6:%lx",
		tdvm_n, tdvm_db_addr[0], (unsigned long)&hw_wp1, tdvm_dr6[0]);
	report(tdvm_n == 1 &&
		   tdvm_db_addr[0] == ((unsigned long)&hw_wp1) && tdvm_dr6[0] == 0xffff4ff2,
		   "hw watchpoint (test that dr6.BS is not cleared)");
}

static void test9(void)
{
	extern unsigned char hw_wp2;
	tdvm_n = 0;
	write_dr6(0);

	asm volatile(
		"mov $42,%%rax\n\t"
		"mov %%rax,%0\n\t; hw_wp2:"
		: "=m" (value) : : "rax");
	report(tdvm_n == 1 &&
		   tdvm_db_addr[0] == ((unsigned long)&hw_wp2) && tdvm_dr6[0] == 0xffff0ff2,
		   "hw watchpoint (test that dr6.BS is not set)");

}

static void test10(void)
{
	extern unsigned char sw_icebp;
	tdvm_n = 0;
	write_dr6(0);
	asm volatile(".byte 0xf1; sw_icebp:");
	report(tdvm_n == 1 &&
		   tdvm_db_addr[0] == (unsigned long)&sw_icebp && tdvm_dr6[0] == 0xffff0ff0,
		   "icebp");
}

static void test11(void)
{
	/*
	 * Each invocation of the handler should shift n by 1 and set bit 0 to 1.
	 * We expect a single invocation, so n should become 3.  If the entry
	 * RIP is wrong, or if the handler is executed more than once, the value
	 * will not match.
	 */
	tdvm_n = 1;
	asm volatile(
		"clc\n\t"
		"mov %0,%%ss\n\t"
		".byte 0x2e, 0x2e, 0xf1"
		: "=m" (value) : : "rax");
	report(tdvm_n == 3,
		   "MOV SS + watchpoint + ICEBP");
}

static void test12(void)
{
	/*
	 * Here the #DB handler is invoked twice, once as a software exception
	 * and once as a software interrupt.
	 */
	tdvm_n = 1;
	p_info("test12 software exception");
	asm volatile(
		"clc\n\t"
		"mov %0,%%ss\n\t"
		: "=m" (value) : : "rax");
	p_info("test12 software interrupt");
	asm volatile("int $1");
	report(tdvm_n == 7,
		   "MOV SS + watchpoint + int $1 ");
}

static void test13(void)
{
	extern unsigned char sw_bp2;
	tdvm_n = 1;
	tdvm_bp_addr = 0;
	asm volatile(
		"mov %0,%%ss\n\t"
		".byte 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0x2e, 0xcc\n\t"
		"sw_bp2:"
		: "=m" (value) : : "rax");
	report(tdvm_n == 3 && tdvm_bp_addr == (unsigned long)&sw_bp2,
		   "MOV SS + watchpoint + INT3");
}

static int __init debug_start(void)
{
	p_info("tdvm_debug_inside start\n");

	tdvm_test_stage = 1;
	test1();
	test2();
	test3();
	test4();
	test5();
	test6();
	test7();
	test8();
	test9();
	test10();

	write_dr7(0x400);
	write_dr7(0x00f0040a); // 4-byte read or write
	value = __KERNEL_DS;
	p_info("kernel_ds %d", __KERNEL_DS);

	tdvm_test_stage = 2;
	test11();
	test12();
	test13();

	tdvm_test_stage = 0;
	return 0;
}

static void report(bool pass, char * test)
{
	if (pass) {
		p_pass("%s", test);
	} else {
		p_fail("%s", test);
	}
}

static inline void write_cr4(ulong val)
{
	asm volatile ("mov %0, %%cr4" : : "r"(val) : "memory");
}

static inline ulong read_cr4(void)
{
	ulong val;
	asm volatile ("mov %%cr4, %0" : "=r"(val) : : "memory");
	return val;
}

static inline void write_dr4(ulong val)
{
	asm volatile ("mov %0, %%dr4" : : "r"(val) : "memory");
}

static inline ulong read_dr4(void)
{
	ulong val;
	asm volatile ("mov %%dr4, %0" : "=r"(val));
	return val;
}

static inline void write_dr0(void *val)
{
	asm volatile ("mov %0, %%dr0" : : "r"(val) : "memory");
}

static inline void write_dr1(void *val)
{
	asm volatile ("mov %0, %%dr1" : : "r"(val) : "memory");
}

static inline void write_dr6(ulong val)
{
	asm volatile ("mov %0, %%dr6" : : "r"(val) : "memory");
}

static inline void write_dr7(ulong val)
{
	asm volatile ("mov %0, %%dr7" : : "r"(val) : "memory");
}

static void __exit debug_end(void)
{
	p_info("tdvm_debug_inside end\n");
}

module_init(debug_start);
module_exit(debug_end);
