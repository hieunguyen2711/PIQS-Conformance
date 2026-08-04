/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsmeta;

import java.text.DecimalFormat;
import java.util.Date;

/**
 *
 * @author kim2
 */
// Transaction class
class Transaction {
    private Date transactionDate;
    private String type;
    private double amount;
    private double balanceAfterTransaction;
    private String currency;

    public Transaction(String type, double amount, double balanceAfterTransaction, String currency) {
        this.transactionDate = new Date();
        this.type = type;
        this.amount = amount;
        this.balanceAfterTransaction = balanceAfterTransaction;
        this.currency = currency;
    }

    @Override
    public String toString() {
        DecimalFormat df = new DecimalFormat("$##0.00");
        return transactionDate.toString() + " - " + type + " " + df.format(amount) + " " + currency + " - Balance: " + df.format(balanceAfterTransaction) + " " + currency;
    }
}
