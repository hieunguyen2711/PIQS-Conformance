/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswscopilot;

import java.util.ArrayList;
import java.util.Date;

/**
 *
 * @author kim2
 */
// Observer Pattern
class AuditLog implements TransactionObserver {
    private ArrayList<String> logs = new ArrayList<>();

    @Override
    public void notify(Transaction transaction) {
        logAction(transaction.toString());
    }

    public void logAction(String logEntry) {
        logs.add(new Date().toString() + " - " + logEntry);
    }

    public void showLogs() {
        for (String log : logs) {
            System.out.println(log);
        }
    }
}



