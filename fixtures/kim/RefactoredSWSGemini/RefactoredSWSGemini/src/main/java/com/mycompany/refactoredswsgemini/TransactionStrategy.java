/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswsgemini;

/**
 *
 * @author kim2
 */
// Interface for transaction strategies (Strategy Pattern)
interface TransactionStrategy {
    void execute(Wallet wallet, double amount);
}
