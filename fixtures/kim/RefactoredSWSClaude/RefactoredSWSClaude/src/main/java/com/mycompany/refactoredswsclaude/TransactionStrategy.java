/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
// -------------------- Strategy Pattern Start --------------------
interface TransactionStrategy {
    String execute(Wallet wallet, double amount);
}