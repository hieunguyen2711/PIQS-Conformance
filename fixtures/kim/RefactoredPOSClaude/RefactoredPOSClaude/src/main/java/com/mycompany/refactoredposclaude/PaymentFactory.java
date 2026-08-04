/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredposclaude;

/**
 *
 * @author kim2
 */
// FACTORY METHOD PATTERN: PaymentFactory interface
interface PaymentFactory {
    PaymentStrategy createPayment();
}