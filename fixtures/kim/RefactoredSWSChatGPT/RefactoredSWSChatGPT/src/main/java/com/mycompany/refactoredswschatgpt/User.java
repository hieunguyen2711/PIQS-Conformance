/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswschatgpt;

import java.util.HashMap;
import java.util.Map;

/**
 *
 * @author kim2
 */
class User {
    String name;
    String password;
    Map<String, Wallet> wallets;
    Observer auditLog;

    public User(String name, String password, Observer auditLog) {
        this.name = name;
        this.password = password;
        this.wallets = new HashMap<>();
        this.auditLog = auditLog;
        auditLog.update("User created: " + name);
    }

    public boolean authenticate(String password) {
        return this.password.equals(password);
    }

    // Factory Method Pattern
    public void addWallet(String currency) {
        if (!wallets.containsKey(currency)) {
            Wallet newWallet = new Wallet(currency);
            wallets.put(currency, newWallet);
            auditLog.update("Wallet added: " + currency);
        }
    }

    public Wallet getWallet(String currency) {
        return wallets.get(currency);
    }

    public void showAllBalances() {
        wallets.forEach((currency, wallet) -> {
            wallet.showBalance();
        });
    }
}