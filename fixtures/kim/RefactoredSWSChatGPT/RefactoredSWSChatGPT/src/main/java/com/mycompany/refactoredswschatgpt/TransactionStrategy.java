/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Interface.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

/**
 *
 * @author kim2
 */
// Strategy Pattern Interface
interface TransactionStrategy {
    void execute(Transaction transaction, Wallet wallet);
}
