/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
// STRATEGY PATTERN: Payment interface
interface PaymentStrategy {
    void processPayment(double amount);
}

