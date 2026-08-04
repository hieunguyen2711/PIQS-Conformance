/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswsmeta;

/**
 *
 * @author kim2
 */
// TransactionStrategy interface (Strategy pattern)
interface TransactionStrategy {
    void executeTransaction(Wallet wallet, double amount);
}
