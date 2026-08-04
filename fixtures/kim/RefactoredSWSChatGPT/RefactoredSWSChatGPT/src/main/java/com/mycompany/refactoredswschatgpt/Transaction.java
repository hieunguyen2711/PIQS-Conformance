/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

import java.text.DecimalFormat;
import java.util.Date;

/**
 *
 * @author kim2
 */
class Transaction {
    Date transactionDate;
    String type;
    double amount;
    double balanceAfterTransaction;
    String currency;
    TransactionStrategy strategy;

    public Transaction(String type, double amount, String currency, TransactionStrategy strategy) {
        this.transactionDate = new Date();
        this.type = type;
        this.amount = amount;
        this.currency = currency;
        this.strategy = strategy;
    }

    @Override
    public String toString() {
        DecimalFormat df = new DecimalFormat("$##0.00");
        return transactionDate.toString() + " - " + type + " " + df.format(amount) + " " + currency + " - Balance: " + df.format(balanceAfterTransaction) + " " + currency;
    }
}