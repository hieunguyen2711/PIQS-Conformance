/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.smartwallet;

import java.text.DecimalFormat;
import java.util.ArrayList;

/**
 *
 * @author kim2
 */
public class Wallet {
    private double balance;
    private ArrayList<Transaction> transactions;
    private String currency;

    public Wallet(String currency) {
        this.balance = 0.0;
        this.transactions = new ArrayList<>();
        this.currency = currency;
    }

    public void addFunds(double amount) {
        balance += amount;
        transactions.add(new Transaction("Deposit", amount, balance, currency));
    }

    public String makePayment(double amount) {
        if (amount <= balance) {
            balance -= amount;
            transactions.add(new Transaction("Payment", amount, balance, currency));
            return "Payment successful.";
        } else {
            return "Insufficient funds.";
        }
    }

    public void showBalance() {
        DecimalFormat df = new DecimalFormat("$##0.00");
        System.out.println("Current Balance in " + currency + ": " + df.format(balance));
    }

    public void showTransactions() {
        for (Transaction t : transactions) {
            System.out.println(t);
        }
    }    
}
