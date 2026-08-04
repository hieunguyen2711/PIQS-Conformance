/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

/**
 *
 * @author kim2
 */
// Strategy Pattern
interface TransactionStrategy {
    String execute(double amount, Wallet wallet);
}

