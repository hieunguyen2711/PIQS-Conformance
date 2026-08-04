/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

import java.util.ArrayList;
import java.util.Date;

/**
 *
 * @author kim2
 */
class AuditLog implements Observer {
    private ArrayList<String> logs = new ArrayList<>();

    @Override
    public void update(String message) {
        logs.add(new Date().toString() + " - " + message);
    }

    public void showLogs() {
        for (String log : logs) {
            System.out.println(log);
        }
    }
}
// -------------------- Observer Pattern End --------------------

