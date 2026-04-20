################################################################################
# Automatically-generated file. Do not edit!
# Toolchain: GNU Tools for STM32 (13.3.rel1)
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../user_files/src/tilt_ctrl.c 

OBJS += \
./user_files/src/tilt_ctrl.o 

C_DEPS += \
./user_files/src/tilt_ctrl.d 


# Each subdirectory must supply rules for building sources it contributes
user_files/src/%.o user_files/src/%.su user_files/src/%.cyclo: ../user_files/src/%.c user_files/src/subdir.mk
	arm-none-eabi-gcc "$<" -mcpu=cortex-m0 -std=gnu11 -g3 -DDEBUG -DUSE_HAL_DRIVER -DSTM32F042x6 -c -I../Core/Inc -I../Drivers/STM32F0xx_HAL_Driver/Inc -I../Drivers/STM32F0xx_HAL_Driver/Inc/Legacy -I../Drivers/CMSIS/Device/ST/STM32F0xx/Include -I../Drivers/CMSIS/Include -I"/Users/jaspertan/Desktop/SCU/MECH208/Final_Project/Code/STM32_Code/tilt_plate/user_files/inc" -O0 -ffunction-sections -fdata-sections -Wall -fstack-usage -fcyclomatic-complexity -MMD -MP -MF"$(@:%.o=%.d)" -MT"$@" --specs=nano.specs -mfloat-abi=soft -mthumb -o "$@"

clean: clean-user_files-2f-src

clean-user_files-2f-src:
	-$(RM) ./user_files/src/tilt_ctrl.cyclo ./user_files/src/tilt_ctrl.d ./user_files/src/tilt_ctrl.o ./user_files/src/tilt_ctrl.su

.PHONY: clean-user_files-2f-src

