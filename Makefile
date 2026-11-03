# Naruto Shippuden: Ultimate Ninja 4 (USA) - decompilacao
BASENAME := SLUS_218.62
TOOLS    := tools/bin
CROSS    := $(TOOLS)/binutils/mips-ps2-decompals-
AS       := $(CROSS)as
LD       := $(CROSS)ld
OBJCOPY  := $(CROSS)objcopy
PYTHON   ?= python3

ASFLAGS  := -EL -march=r5900 -mabi=eabi -G0 -no-pad-sections -I include -I asm
BUILD    := build
ELF      := $(BUILD)/$(BASENAME).elf
ROM      := $(BUILD)/$(BASENAME).rom
LDSCRIPT := $(BUILD)/$(BASENAME).ld

S_FILES   := $(shell find asm -name '*.s' -not -path 'asm/funcs/*' 2>/dev/null)
BIN_FILES := $(shell find assets -name '*.bin' 2>/dev/null)
O_FILES   := $(S_FILES:%=$(BUILD)/%.o) $(BIN_FILES:%=$(BUILD)/%.o)

.PHONY: all tools setup check clean distclean match progress

all: check

tools:
	$(PYTHON) tools/setup_tools.py

setup:
	$(PYTHON) tools/setup.py

$(BUILD)/%.s.o: %.s
	@mkdir -p $(dir $@)
	$(AS) $(ASFLAGS) -o $@ $<

$(BUILD)/%.bin.o: %.bin
	@mkdir -p $(dir $@)
	printf '.section .data, "wa"\n.incbin "%s"\n' $< | $(AS) $(ASFLAGS) -o $@ -

$(ELF): $(O_FILES) $(LDSCRIPT)
	$(LD) -EL -T $(LDSCRIPT) -T config/auto/undefined_syms_auto.txt -T config/auto/undefined_funcs_auto.txt \
	      --no-check-sections -Map $(BUILD)/$(BASENAME).map -o $@

$(ROM): $(ELF)
	$(OBJCOPY) -O binary --only-section=.main --only-section=.data_a --only-section=.late --only-section=.data_b $< $@

# Compara o executavel reconstruido com o original (byte a byte)
check: $(ROM)
	@$(PYTHON) tools/check.py $(ROM) baserom/$(BASENAME).rom

# Compara uma funcao em C com o original: make match FUNC=func_00123456
match:
	@test -n "$(FUNC)" || (echo "uso: make match FUNC=func_XXXXXXXX" >&2; exit 2)
	@$(PYTHON) tools/match.py $(FUNC)

progress:
	@$(PYTHON) tools/progress.py

clean:
	rm -rf $(BUILD)/asm $(BUILD)/assets $(BUILD)/src $(BUILD)/*.elf $(BUILD)/*.rom $(BUILD)/*.map

distclean: clean
	rm -rf asm assets build config/auto
