/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredposgemini;

/**
 *
 * @author kim2
 */
// Factory Method Pattern: Payment Factory
interface PaymentFactory {
    Payment createPayment(double amount);
}

